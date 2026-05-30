import sys
sys.path.append('.')
from tts import SparkTTS
import wave

print("Initializing TTS...")
tts = SparkTTS()

def test_synthesis(text, suffix=""):
    test_text = text + suffix
    print(f"\nSynthesizing: '{test_text}'")
    audio = tts.voice_en.synthesize(test_text)
    audio_bytes = b"".join(a.audio_int16_bytes for a in audio)
    duration = len(audio_bytes) / (22050 * 2)
    print(f"Result: {len(audio_bytes)} bytes | {duration:.2f} seconds")
    return audio_bytes

# Test without punctuation
b1 = test_synthesis("Google AI Pro")
# Test with trailing period
b2 = test_synthesis("Google AI Pro", ".")
# Test with trailing space and period
b3 = test_synthesis("Google AI Pro", " .")

print("\nDone testing.")
