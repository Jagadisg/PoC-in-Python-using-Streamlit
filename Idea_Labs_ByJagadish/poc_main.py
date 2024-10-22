import os
import requests
from dotenv import load_dotenv

import random
import asyncio
import librosa
import pyttsx3
import assemblyai as aai
import streamlit as st
from pathlib import Path
from loguru import logger
import moviepy.editor as mp
from pydub import AudioSegment
from utils.helper_utils import filepath_name
from utils.audio_sync_utils import insert_silences_into_ai_audio


load_dotenv()


async def main():
    """
    Main purpose to manage the Streamlit application. lets the user upload a video file, extract the audio, transcribing it, then use Azure OpenAI GPT-4 to generate text-to--speech audio from the corrected text, so merging the corrected AI-generated audio back with the original video.     
    """    
    
    st.title("Video Upload and Audio Processing PoC")
    
    # Step 1: Upload a video file
    video_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "mkv"])
    
    if video_file is not None:
        await vedio_conversion(video_file)


async def vedio_conversion(video_file):
    """
    Handles the video conversion steps including audio extraction, transcribing, 
    text correction, text to ai speech, and merging the AI audio into the video.
        
    Args:
        video_file: Uploaded video file.
    """
    
    directory = "uploads"
    Path(directory).mkdir(parents=True, exist_ok=True)        
    temp_video_path = await save_uploaded_file(video_file)
    original_audio = AudioSegment.from_file(temp_video_path)
    logger.error(original_audio)
    # a, sr = librosa.load(temp_video_path)
    # logger.info(a)
    # logger.info(sr)
    st.video(video_file) 
    print(temp_video_path)
    # Step 2: Extract audio from the video
    with st.spinner("Extracting audio from the video..."):
        temp_audio_path, duration = await extract_audio_from_video(temp_video_path)
        ai_audio = AudioSegment.from_wav(temp_audio_path)
        logger.error(ai_audio)
        st.success("Audio extracted successfully.")

    # Step 3: Transcribe the audio using AssemblyAI
    with st.spinner("Transcribing audio..."):
        transcribed_segments1, combined_text = await transcribe_audio(temp_audio_path)
        if duration <= 30:
            combined_text = await add_space_by_segment(segments=transcribed_segments1)

    # Step 4: Text correction using Azure OpenAI
    if combined_text:
        with st.spinner("Correcting the transcribed text..."):
            corrected_text = await correct_text_using_gpt(combined_text)
             
    # Step 5: Convert corrected text to speech
    if corrected_text:
        with st.spinner("Converting text to speech..."):
            logger.info(corrected_text)
            ai_audio_path = await text_to_speech(corrected_text,temp_video_path)  
            st.error(ai_audio_path)          
            uploads_dir = Path(__file__).parent.parent
            logger.info(os.listdir(uploads_dir))
            st.success("Text-to-speech conversion completed.")
            if duration > 30:
                ai_audio_output_path = f"{os.path.splitext(temp_video_path)[0]}{random.randint(10,99)}_final_audio.wav"
                logger.info(ai_audio_output_path)
                await insert_silences_into_ai_audio(temp_audio_path,ai_audio_path,ai_audio_output_path)
                ai_audio_path = ai_audio_output_path
            # Step 6: Merge AI-generated audio with the original video
            with st.spinner("Merging AI-generated audio with video..."):
                new_video_path = await merge_audio_video(ai_audio_path, temp_video_path)

            
    
    # Clean up temporary files
    # await cleanup_files([temp_video_path,temp_audio_path,ai_audio_path,ai_audio_path,ai_audio_path,new_video_path])


async def save_uploaded_file(uploaded_file):
    """
    Save the uploaded file.

    Args:
        uploaded_file: The file uploaded via Streamlit.
        output_path (str): Path to save the uploaded file.

    Returns:
        str: Path to the saved file.
    """
    save_path = await filepath_name(uploaded_file=uploaded_file)        
    with open(save_path, "wb") as f:
        f.write(uploaded_file.read())
    return save_path


async def extract_audio_from_video(video_path):
    """
    Extract audio from the input vedio file

    Args:
        video_path (str): Path to the video file.

    Returns:
        str: Path to the extracted audio file.
    """
    try:
        video_clip = mp.VideoFileClip(video_path)
        audio_clip = video_clip.audio
        og_audio_path = f"{os.path.splitext(video_path)[0]}{random.randint(10,99)}og_audio.wav"
        print(f"{og_audio_path} {'-'*20}")
        audio_clip.write_audiofile(og_audio_path, logger=None)
        duration_seconds = audio_clip.duration
        video_clip.close()
        return og_audio_path, duration_seconds
    except Exception as e:
        logger.error(f"Failed to extract audio: {str(e)}")
        st.error("Error in extracting audio.")
        return None


async def transcribe_audio(audio_path):
    """
    Uses AssemblyAI API to transcribe the given audio file and create segments.
    
    Args:
        audio_path (str): Audio file path.
    
    Returns:
        list: A list of segments containing id, start, end, and text.
    """
    aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
    transcriber = aai.Transcriber()
    
    try:
        transcript = transcriber.transcribe(audio_path)
        segments = []
        combined_text = ""
        for i, word in enumerate(transcript.words):
            if i == 0 or word.start != transcript.words[i-1].end:
                segments.append({
                    'id': len(segments),
                    'start': word.start / 1000.0,
                    'end': word.end / 1000.0,
                    'text': word.text
                })
                combined_text += word.text + " "
            else:
                segments[-1]['end'] = word.end / 1000.0
                segments[-1]['text'] += ' ' + word.text
                combined_text += word.text + " "
        logger.info(segments)
        logger.info(combined_text)
        return segments, combined_text

    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return []



async def correct_text_using_gpt(transcribed_text):
    """
    Sends the transcribed text to Azure OpenAI for text correction.

    Args:
        transcribed_text (str): The text that needs correction.

    Returns:
        str: Corrected text.
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": os.getenv('AZURE_OPENAI_KEY')
    }
    prompt = f"Transcribed text: {transcribed_text}. Correct the transcribed text by removing any grammatical mistakes and filler words like 'umm', 'hmm', etc. Preserve the existing spacing between words, do not remove or add any extra spaces that are not part of the original text."
    
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000
    }

    try:
        azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        response = requests.post(azure_endpoint, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            logger.info(result["choices"][0]["message"]["content"].strip())
            return result["choices"][0]["message"]["content"].strip()
        else:
            logger.error(f"GPT-4 API error: {response.status_code} - {response.text}")
            st.error("Failed to correct text.")
            return None
    except Exception as e:
        logger.error(f"Error in GPT-4 request: {str(e)}")
        st.error("Error connecting to GPT-4.")
        return None


async def text_to_speech(text, video_path):
    """
    Runs the given text through pyttsx3 text-to-speech engine.
    
    Args:
        text (str): The text to convert to speech.
        video_path (str): The path to the video file.
    
    Returns:
        str: The file path of the AI-generated audio.
    """
    try:
        # Load the original audio from the video
        original_audio, sr = librosa.load(video_path)
        tempo, _ = librosa.beat.beat_track(y=original_audio, sr=sr)

        # Initialize pyttsx3 engine and set the speech rate to match the audio tempo
        engine = pyttsx3.init()
        engine.setProperty('rate', tempo)

        # Generate a random name for the ai_audio.wav file
        ai_audio_filename = f"{os.path.splitext(os.path.basename(video_path))[0]}{random.randint(10, 99)}ai_audio.wav"

        # Resolve the uploads directory
        uploads_dir = Path(__file__).resolve().parent.parent / 'uploads'

        # Ensure the uploads directory exists
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct the full path for ai_audio.wav
        ai_audio_path = uploads_dir / ai_audio_filename
        
        # Log the path where the file will be saved
        logger.info(f"AI audio will be saved at: {ai_audio_path}")

        # Save the text-to-speech audio to the specified path
        engine.save_to_file(text, str(ai_audio_path))  # Note: ensure the path is a string for pyttsx3
        engine.runAndWait()

        # Return the full path of the AI-generated audio
        return str(ai_audio_path)

    except Exception as e:
        logger.error(f"Text-to-speech conversion failed: {str(e)}")
        st.error("Error in text-to-speech conversion.")
        return None



async def merge_audio_video(new_audio_path, video_path):
    
    """
    Combines the original video file with the artificial intelligence produced audio.
    
    Args:
        new_audio_path (str): Path to the ai audio file.
        video_clip: Video clip object of the original video.
    """
    try:
        video_clip = mp.VideoFileClip(video_path)
        ai_audio = mp.AudioFileClip(new_audio_path)
        
        
        video_with_new_audio = video_clip.set_audio(ai_audio)
        new_video_path = f"{os.path.splitext(video_path)[0]}{random.randint(10,99)}_new.mp4"
        video_with_new_audio.write_videofile(new_video_path, codec='libx264', audio_codec='aac', verbose=False, logger=None)
        
        video_clip.close()
        ai_audio.close()
        
        st.video(new_video_path)
        st.success("Video processing completed with synchronized audio.")
        return new_video_path
    except Exception as e:
        logger.error(f"Error merging audio and video: {str(e)}")
        st.error("Failed to merge audio and video.")


async def add_space_by_segment(combined_text:str="",segments:list = None) -> str:
    '''
    Adding the extra space by calculating the current end and start of next segment (where 0.1 second equals to one space)
    
    Args:
        default (combined_text) : Add the combined text after extra space to create silence in audio for particular timestamp.
        segments : Contains list of start, end and text
        
    Return: 
        combined text.
    '''
    try:
        for i in range(len(segments)):        
            combined_text += segments[i]["text"] + " "
            
            if i < len(segments) - 1:
                gap = segments[i + 1]["start"] - segments[i]["end"]
                gap_in_ms = gap * 1000
                spaces = int(gap_in_ms / 10)
                combined_text += " " * spaces              
        print(combined_text)            
    except Exception:
        st.error("Error in adding space functionality")
    return combined_text

async def cleanup_files(file_paths):
    """
    Deletes temporary files used during the conversion.

    Args:
        file_paths (list): List of file paths to delete.
    """
    for file_path in file_paths:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not delete {file_path}: {str(e)}")
                st.error("Error in file deletion")


if __name__ == "__main__":
    
    asyncio.run(main())
