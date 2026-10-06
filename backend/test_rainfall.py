import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from fastapi import HTTPException
from app.services.rainfall import calculate_antecedent_rainfall

class TestRainfallService(unittest.TestCase):

    @patch("app.services.rainfall.httpx.get")
    def test_successful_rainfall_retrieval(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily": {
                "time": [
                    "2025-08-10", "2025-08-11", "2025-08-12", "2025-08-13", "2025-08-14",
                    "2025-08-15", "2025-08-16", "2025-08-17", "2025-08-18", "2025-08-19"
                ],
                "rain_sum": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            }
        }
        mock_get.return_value = mock_response

        target_date = date(2025, 8, 20)
        result = calculate_antecedent_rainfall(17.3850, 78.4867, target_date)
        
        # Check T1d (D-1 = 10.0)
        self.assertEqual(result.T1d, 10.0)
        # Check cumulative calculations
        self.assertEqual(result.T2d, 19.0)
        self.assertEqual(result.T3d, 27.0)
        self.assertEqual(result.T4d, 34.0)
        self.assertEqual(result.T5d, 40.0)
        self.assertEqual(result.T6d, 45.0)
        self.assertEqual(result.T7d, 49.0)
        self.assertEqual(result.T8d, 52.0)
        self.assertEqual(result.T9d, 54.0)
        self.assertEqual(result.T10d, 55.0)
        
        # Verify Open-Meteo URL and dates were correctly queried
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["start_date"], "2025-08-10")
        self.assertEqual(kwargs["params"]["end_date"], "2025-08-19")

    @patch("app.services.rainfall.httpx.get")
    def test_invalid_lat_long(self, mock_get):
        from httpx import HTTPStatusError, Request, Response
        mock_get.side_effect = HTTPStatusError(
            message="Bad Request",
            request=Request("GET", "https://api"),
            response=Response(400)
        )
        with self.assertRaises(HTTPException) as context:
            calculate_antecedent_rainfall(900.0, 900.0, date(2025, 8, 20))
        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("Open-Meteo API error: 400", context.exception.detail)

    def test_future_date(self):
        future_date = date(2100, 1, 1)
        with self.assertRaises(HTTPException) as context:
            calculate_antecedent_rainfall(17.3850, 78.4867, future_date)
        self.assertEqual(context.exception.status_code, 400)
        self.assertIn("Target date cannot be in the future", context.exception.detail)

    @patch("app.services.rainfall.httpx.get")
    def test_insufficient_historical_data(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily": {
                "time": ["2025-08-18", "2025-08-19"],
                "rain_sum": [9.0, 10.0]
            }
        }
        mock_get.return_value = mock_response
        with self.assertRaises(HTTPException) as context:
            calculate_antecedent_rainfall(17.3850, 78.4867, date(2025, 8, 20))
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Insufficient historical rainfall data", context.exception.detail)

    @patch("app.services.rainfall.httpx.get")
    def test_network_failure(self, mock_get):
        from httpx import RequestError, Request
        mock_get.side_effect = RequestError("Connection failed", request=Request("GET", "https://api"))
        with self.assertRaises(HTTPException) as context:
            calculate_antecedent_rainfall(17.3850, 78.4867, date(2025, 8, 20))
        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("Open-Meteo network failure", context.exception.detail)

    @patch("app.services.rainfall.httpx.get")
    def test_null_rainfall_response(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "daily": {
                "time": [
                    "2025-08-10", "2025-08-11", "2025-08-12", "2025-08-13", "2025-08-14",
                    "2025-08-15", "2025-08-16", "2025-08-17", "2025-08-18", "2025-08-19"
                ],
                "rain_sum": [1.0, 2.0, None, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            }
        }
        mock_get.return_value = mock_response
        with self.assertRaises(HTTPException) as context:
            calculate_antecedent_rainfall(17.3850, 78.4867, date(2025, 8, 20))
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Missing or null rainfall values", context.exception.detail)

if __name__ == "__main__":
    unittest.main()
