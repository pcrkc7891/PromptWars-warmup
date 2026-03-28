import pytest
import json
import html
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

def test_404_handling(client):
    """Test the robust 404 URL shielding."""
    response = client.get("/random-invalid-url-sweep")
    assert response.status_code == 404
    assert response.is_json
    assert "Resource not found" in response.get_json()["error"]

def test_invalid_content_type(client):
    """Test that non-JSON payloads are aggressively rejected."""
    response = client.post("/process", data="raw string here")
    assert response.status_code == 415
    assert response.is_json

def test_process_no_message(client):
    """Test the API rejection of missing data."""
    with patch("app.api_key", "dummy_key"):
        with patch("app.model", MagicMock()):
            response = client.post("/process", json={})
            assert response.status_code == 400
            data = response.get_json()
            assert "Invalid JSON" in data["error"] or "No message parameter explicitly provided" in data["error"]

def test_process_missing_api_key(client):
    """Test that hitting the route without an API key gracefully blocks execution (Security Coverage)."""
    with patch("app.api_key", None):
        response = client.post("/process", json={"message": "Valid string"})
        assert response.status_code == 500
        data = response.get_json()
        assert "Gemini API key not configured" in data["error"]

@patch("app.model")
def test_process_sanitizes_xss(mock_model_global, client):
    """Test that malicious HTML/JS tags get escaped before being passed to the Generative Model."""
    mock_result = MagicMock()
    # Mocking standard successful output purely so the function finishes successfully.
    mock_result.text = '{"severity": "High", "intent": "Rescue", "location_summary": "123", "actionable_recommendation": "Step", "priority_level": 5}'
    mock_model_global.generate_content.return_value = mock_result

    with patch("app.api_key", "dummy_key"):
        xss_payload = "<script>alert('pwned')</script> I need help!"
        response = client.post("/process", json={"message": xss_payload})
        
        assert response.status_code == 200
        
        # Verify the model received the safely escaped string, NOT the raw script tags.
        escaped_payload = html.escape(xss_payload)
        mock_model_global.generate_content.assert_called_once_with(escaped_payload)

@patch("app.model")
def test_process_success(mock_model_global, client):
    """Test a successful Gemini extraction and structuring process."""
    mock_result = MagicMock()
    # Mock the exact JSON string format Gemini 1.5 Flash will return
    mock_result.text = '{"severity": "High", "intent": "Rescue", "location_summary": "123 Elm St", "actionable_recommendation": "Dispatch swift water boat.", "priority_level": 5}'
    mock_model_global.generate_content.return_value = mock_result

    with patch("app.api_key", "dummy_key"):
        response = client.post("/process", json={"message": "We are drowning at 123 Elm St!"})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["severity"] == "High"
        assert data["priority_level"] == 5
        assert "Dispatch" in data["actionable_recommendation"]
