import os
from pathlib import Path
from pydub import AudioSegment
from pydub.silence import detect_silence


async def insert_silences_into_ai_audio(original_audio_path, ai_audio_path, audio_output_filepath):

    uploads_dir = Path(__file__).parent / 'uploads'
    ai_audio_path = Path(ai_audio_path).name
    original_audio = Path(original_audio).name
    ai_audio_path = uploads_dir / ai_audio_path    
    original_audio = uploads_dir / original_audio
    original_audio = AudioSegment.from_file(original_audio)
    ai_audio = AudioSegment.from_wav(ai_audio_path)
    
    silence_ranges_original = detect_silence(original_audio, min_silence_len=500, silence_thresh=-40)
    silence_ranges_ai = detect_silence(ai_audio, min_silence_len=500, silence_thresh=-40)
    
    print(f"Original audio silence ranges: {silence_ranges_original}")
    print(f"AI audio silence ranges: {silence_ranges_ai}")
    
    time_offset = 0
    
    adjusted_ai_audio = AudioSegment.empty()
    
    i = 0
    j = 0
    while i < len(silence_ranges_original) and j < len(silence_ranges_ai):
        start_ori, end_ori = silence_ranges_original[i]
        start_ai, end_ai = silence_ranges_ai[j]

        if start_ori < start_ai:
            reduce_ms = 0
            if i != 0:
                reduce_ms = 20
            silence_duration = (end_ori - start_ori) - reduce_ms
            silence = AudioSegment.silent(duration=silence_duration)
            adjusted_ai_audio += silence
            print(f"Inserting silence at {start_ori} ms for {silence_duration} ms")
            i += 1
        else:
            adjusted_end = start_ai+30
            if adjusted_end > len(ai_audio):
                adjusted_end = len(ai_audio)
            adjusted_ai_audio += ai_audio[time_offset:adjusted_end]
            time_offset = end_ai
            j += 1

    if time_offset < len(ai_audio):
        adjusted_ai_audio += ai_audio[time_offset:]

    adjusted_ai_audio.export(audio_output_filepath, format="wav")
    print("Silence-adjusted AI audio created.")


if __name__ == "__main__":    
    pass

