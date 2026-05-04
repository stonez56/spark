import numpy as np
from faster_whisper import WhisperModel

class SparkSTT:
    def __init__(self, model_size="base"):
        print(f"Loading faster-whisper model '{model_size}'...")
        # compute_type="int8" is good for speed/memory on CPU
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_data: np.ndarray, sample_rate=16000):
        """
        Transcribes numpy audio array. 
        faster-whisper expects float32 array in [-1.0, 1.0].
        """
        # Convert int16 to float32
        audio_float32 = audio_data.astype(np.float32) / 32768.0
        
        print("Transcribing audio...")
        # Removed language="en" to allow auto-detection of Chinese or English
        segments, info = self.model.transcribe(audio_float32, beam_size=5)
        
        text = ""
        for segment in segments:
            text += segment.text + " "
            
        return text.strip()
