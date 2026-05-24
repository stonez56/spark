import unittest
from unittest.mock import MagicMock, patch
from tts import SparkTTS

class TestSparkTTS(unittest.TestCase):
    @patch('tts.PiperVoice')
    def setUp(self, mock_piper_voice):
        """Set up mock voices before each test run."""
        self.mock_voice_zh = MagicMock()
        self.mock_voice_en = MagicMock()
        
        # Configure PiperVoice.load to return Chinese then English mocks
        mock_piper_voice.load.side_effect = [self.mock_voice_zh, self.mock_voice_en]
        
        self.tts = SparkTTS()

    def test_contains_chinese(self):
        """Test the _contains_chinese helper function."""
        self.assertTrue(self.tts._contains_chinese("哈囉阿公"))
        self.assertTrue(self.tts._contains_chinese("Hello 阿公"))
        self.assertFalse(self.tts._contains_chinese("Hello Grandfather"))
        self.assertFalse(self.tts._contains_chinese("12345!"))

    def test_synthesize_pure_chinese(self):
        """Test synthesis of pure Chinese text (should use Chinese voice only)."""
        # Mock synthesis output
        mock_audio_frame = MagicMock()
        mock_audio_frame.audio_int16_bytes = b"\x01\x02"
        self.mock_voice_zh.synthesize.return_value = [mock_audio_frame]
        
        output = self.tts.synthesize("哈囉阿公")
        
        self.assertEqual(output, b"\x01\x02")
        self.mock_voice_zh.synthesize.assert_called_once_with("哈囉阿公")
        self.mock_voice_en.synthesize.assert_not_called()

    def test_synthesize_pure_english(self):
        """Test synthesis of pure English text (should use English voice only)."""
        # Mock synthesis output
        mock_audio_frame = MagicMock()
        mock_audio_frame.audio_int16_bytes = b"\x03\x04"
        self.mock_voice_en.synthesize.return_value = [mock_audio_frame]
        
        output = self.tts.synthesize("Hello Grandfather")
        
        self.assertEqual(output, b"\x03\x04")
        self.mock_voice_en.synthesize.assert_called_once_with("Hello Grandfather")
        self.mock_voice_zh.synthesize.assert_not_called()

    def test_synthesize_mixed_bilingual(self):
        """Test synthesis of mixed English and Chinese text (should use both voices)."""
        # Mock synthesis outputs for each voice
        frame_zh = MagicMock()
        frame_zh.audio_int16_bytes = b"\x10\x10"
        self.mock_voice_zh.synthesize.return_value = [frame_zh]
        
        frame_en = MagicMock()
        frame_en.audio_int16_bytes = b"\x20\x20"
        self.mock_voice_en.synthesize.return_value = [frame_en]
        
        output = self.tts.synthesize("Hello 阿公")
        
        # Hello should route to EN, 阿公 should route to ZH
        self.mock_voice_en.synthesize.assert_called_once_with("Hello")
        self.mock_voice_zh.synthesize.assert_called_once_with("阿公")
        self.assertEqual(output, b"\x20\x20\x10\x10")

if __name__ == "__main__":
    unittest.main()
