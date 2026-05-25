import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Patch dependencies inside ui.py BEFORE importing app, to prevent database/settings side-effects
with patch('ui.reminders_db') as mock_db, patch('ui.settings_manager') as mock_settings:
    from ui import app

class TestSparkUI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Clear mock calls before each test
        app.state.audio_queue = MagicMock()
        app.state.mode_queue = MagicMock()
        app.state.stop_audio_flag = MagicMock()
        app.state.command_queue = MagicMock()
        app.state.current_mode = 'local'
        app.state.current_model = 'gemma3:1b'

    @patch('ui.reminders_db')
    def test_get_reminders(self, mock_reminders_db):
        """Test GET /api/reminders retrieves reminders successfully."""
        mock_reminders = [
            {"id": 1, "message": "Take pill", "times": "08:00", "days_of_week": "0,1,2", "start_date": "2026-05-24", "end_date": "2026-05-25", "is_active": True}
        ]
        mock_reminders_db.get_all_reminders.return_value = mock_reminders

        response = self.client.get("/api/reminders")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mock_reminders)
        mock_reminders_db.get_all_reminders.assert_called_once()

    @patch('ui.reminders_db')
    def test_add_reminder(self, mock_reminders_db):
        """Test POST /api/reminders adds a reminder successfully."""
        payload = {
            "message": "Drink water",
            "times": "14:00",
            "days_of_week": "0,1,2,3,4,5,6",
            "start_date": "2026-05-24",
            "end_date": "2026-05-30",
            "is_active": True
        }
        response = self.client.post("/api/reminders", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_reminders_db.add_reminder.assert_called_once_with(
            "Drink water", "14:00", "0,1,2,3,4,5,6", "2026-05-24", "2026-05-30", True
        )

    @patch('ui.reminders_db')
    def test_update_reminder(self, mock_reminders_db):
        """Test PUT /api/reminders/{id} updates a reminder."""
        payload = {
            "message": "Drink water",
            "times": "14:30",
            "days_of_week": "0,1,2,3,4,5,6",
            "start_date": "2026-05-24",
            "end_date": "2026-05-30",
            "is_active": False
        }
        response = self.client.put("/api/reminders/42", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_reminders_db.update_reminder.assert_called_once_with(
            42, "Drink water", "14:30", "0,1,2,3,4,5,6", "2026-05-24", "2026-05-30", False
        )

    @patch('ui.reminders_db')
    def test_delete_reminder(self, mock_reminders_db):
        """Test DELETE /api/reminders/{id} deletes a reminder."""
        response = self.client.delete("/api/reminders/42")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_reminders_db.delete_reminder.assert_called_once_with(42)

    @patch('ui.settings_manager')
    def test_get_settings(self, mock_settings):
        """Test GET /api/settings loads settings."""
        mock_val = {"patient_name": "阿公", "caregiver_name": "小星"}
        mock_settings.load_settings.return_value = mock_val

        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), mock_val)

    @patch('ui.settings_manager')
    def test_post_settings(self, mock_settings):
        """Test POST /api/settings saves and triggers cache regeneration command."""
        mock_settings.load_settings.return_value = {"patient_name": "阿公", "caregiver_name": "小星", "speaking_speed": "normal"}
        
        response = self.client.post("/api/settings", json={"patient_name": "阿嬤", "caregiver_name": "小花"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        
        mock_settings.save_settings.assert_called_once_with({"patient_name": "阿嬤", "caregiver_name": "小花", "speaking_speed": "normal"})
        app.state.command_queue.put.assert_called_once_with({'type': 'regenerate_cache'})

    @patch('ui.settings_manager')
    def test_post_settings_no_patient_name_change(self, mock_settings):
        """Test POST /api/settings does not trigger cache regeneration when patient_name does not change."""
        mock_settings.load_settings.return_value = {"patient_name": "阿公", "caregiver_name": "小星", "speaking_speed": "normal"}
        
        # Scenario A: patient_name in payload is identical to existing
        response = self.client.post("/api/settings", json={"patient_name": "阿公", "caregiver_name": "小花"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_settings.save_settings.assert_any_call({"patient_name": "阿公", "caregiver_name": "小花", "speaking_speed": "normal"})
        
        # Scenario B: patient_name not even in payload
        response = self.client.post("/api/settings", json={"caregiver_name": "大毛", "speaking_speed": "fast"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        mock_settings.save_settings.assert_any_call({"patient_name": "阿公", "caregiver_name": "大毛", "speaking_speed": "fast"})
        
        # Ensure command_queue was never called
        app.state.command_queue.put.assert_not_called()


    def test_get_status(self):
        """Test GET /api/status returns current mode and model."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"mode": "local", "model": "gemma3:1b"})

    def test_set_mode(self):
        """Test POST /api/set-mode queues the runtime mode switch."""
        response = self.client.post("/api/set-mode", json={"mode": "cloud"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "mode": "cloud"})
        app.state.mode_queue.put.assert_called_once_with("cloud")

if __name__ == "__main__":
    unittest.main()
