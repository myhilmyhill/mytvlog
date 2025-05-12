import unittest
from unittest.mock import patch, MagicMock
import os
import json
from datetime import datetime, timedelta

import poll

class TestRunJob(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_run_job_finished(self, mock_urlopen):
        # play_status = finished → POSTなし
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "play_status": "finished"
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        poll.run_job("http://dummy/status")
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch("urllib.request.urlopen")
    def test_run_job_active(self, mock_urlopen):
        # play_status ≠ finished → POSTされる
        get_response = MagicMock()
        get_response.read.return_value = json.dumps({
            "current_event_id": 123,
            "current_event_service_id": 456,
            "current_event_name": "Example Show",
            "current_event_start_time": "2025-05-13T12:00:00+09:00",
            "current_event_duration": 1800,
            "tot": "2025-05-13T12:05:00+09:00"
        }).encode('utf-8')
        post_response = MagicMock()

        mock_urlopen.side_effect = [
            MagicMock(__enter__=lambda s: get_response),
            MagicMock(__enter__=lambda s: post_response)
        ]

        poll.run_job("http://dummy/status")
        self.assertEqual(mock_urlopen.call_count, 2)

class TestSleepUntilNextInterval(unittest.TestCase):
    @patch("time.sleep")
    def test_sleep_until_next_interval(self, mock_sleep):
        now = datetime(2025, 5, 13, 10, 3, 0)
        with patch("poll.datetime") as mock_datetime:
            mock_datetime.now.return_value = now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            poll.sleep_until_next_interval(interval_minutes=5, delay_seconds=10)
            # 10:05:10 に sleep → 130秒
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            self.assertAlmostEqual(sleep_time, 130, delta=1)

if __name__ == '__main__':
    unittest.main()
