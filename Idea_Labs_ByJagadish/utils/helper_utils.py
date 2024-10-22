import os

import librosa
import numpy as np
from scipy.io.wavfile import write


def silence(audio_segments1, audio1_seg_i, sr1):
    zero_silence = int(((audio_segments1[audio1_seg_i]['start'] - audio_segments1[audio1_seg_i-1]['end'])- 0.090) * sr1)
    return zero_silence


def append_silence_stretched_sample(ai_audio,audio_segments2, sr1, i, silence_duration, temp_speechaudio):
    start = int((audio_segments2[i]['start'] - 0.002) * (sr1))
    end = int((audio_segments2[i]['end']+ 0.090) * (sr1))    
    sample = temp_speechaudio[start:end]
    
    stretched_sample = librosa.effects.time_stretch(sample, rate=0.86)
    updated_ai_audio = np.append(ai_audio, np.concatenate(([0] * silence_duration, stretched_sample)))
    return updated_ai_audio


def write_audio_file(ai_audio, sr2, audio_output_filepath):
    audio_int16 = (ai_audio * 32767).astype(np.int16)
    write(audio_output_filepath, sr2, audio_int16)
    return audio_output_filepath


def filepath_name(uploaded_file=None,folder_path='uploads',filename=None):
    
    if not os.path.exists(folder_path):        
        os.makedirs(folder_path)
    if uploaded_file:
        filename = uploaded_file.name
        print(filename)
    save_path = os.path.join(folder_path, filename)        
    return save_path


if __name__ == "__main__":    
    pass