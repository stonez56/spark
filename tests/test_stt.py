import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from stt import SparkSTT

class TestSparkSTT(unittest.TestCase):
    @patch('stt.WhisperModel')
    def test_init(self, mock_whisper):
        """Verify the WhisperModel is initialized correctly with CPU and int8 compute type."""
        stt = SparkSTT(model_size="tiny")
        mock_whisper.assert_called_once_with("tiny", device="cpu", compute_type="int8")

    @patch('stt.WhisperModel')
    def test_transcribe(self, mock_whisper):
        """Verify transcription properly processes the numpy audio array and joins segments."""
        # Setup mock WhisperModel instance
        mock_model_instance = MagicMock()
        mock_whisper.return_value = mock_model_instance

        # Mock segment objects returned by model.transcribe
        segment_1 = MagicMock()
        segment_1.text = "Hello"
        segment_2 = MagicMock()
        segment_2.text = "world."
        
        mock_model_instance.transcribe.return_value = ([segment_1, segment_2], MagicMock())

        # Initialize SparkSTT (will use mock model)
        stt = SparkSTT(model_size="tiny")

        # Create dummy int16 audio data
        audio_data = np.zeros(16000, dtype=np.int16)
        
        # Perform transcription
        transcription = stt.transcribe(audio_data)

        # Verify results
        self.assertEqual(transcription, "Hello world.")
        
        # Verify the model's transcribe method was called with the float32 array in the expected range
        called_args, called_kwargs = mock_model_instance.transcribe.call_args
        called_audio = called_args[0]
        
        self.assertIsInstance(called_audio, np.ndarray)
        self.assertEqual(called_audio.dtype, np.float32)
        self.assertEqual(called_kwargs.get("beam_size"), 5)

if __name__ == "__main__":
    unittest.main()
