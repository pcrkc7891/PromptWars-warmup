import pytest
import json
from app import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test that the frontend UI is properly served."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ResQ-Route" in response.data

def test_process_no_message(client):
    """Test the API rejection of missing data."""
    # Temporarily set a dummy API key to bypass configuration check constraint locally
    with patch("app.api_key", "dummy_key"):
        response = client.post("/process", json={})
        assert response.status_code == 400
        data = response.get_json()
        assert "No message provided" in data["error"]

@patch("app.genai.GenerativeModel")
def test_process_success(mock_model_class, client):
    """Test a successful Gemini extraction and structuring process."""
    mock_instance = MagicMock()
    mock_result = MagicMock()
    # Mock the exact JSON string format Gemini 1.5 Flash will return
    mock_result.text = '{"severity": "High", "intent": "Rescue", "location_summary": "123 Elm St", "actionable_recommendation": "Dispatch swift water boat.", "priority_level": 5}'
    mock_instance.generate_content.return_value = mock_result
    mock_model_class.return_value = mock_instance

    with patch("app.api_key", "dummy_key"):
        response = client.post("/process", json={"message": "We are drowning at 123 Elm St!"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["severity"] == "High"
        assert data["priority_level"] == 5
        assert "Dispatch" in data["actionable_recommendation"]
