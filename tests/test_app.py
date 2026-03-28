import pytest
import json
import html
from unittest.mock import patch, MagicMock

# Crucial: Mock all intensive GCP instantiations BEFORE app execution loop imports.
with patch("google.cloud.logging.Client"), \
     patch("google.cloud.storage.Client"), \
     patch("google.cloud.error_reporting.Client"), \
     patch("google.cloud.pubsub_v1.PublisherClient"), \
     patch("firebase_admin.initialize_app"), \
     patch("firebase_admin.firestore.client"):
    from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test frontend DOM renders flawlessly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"ResQ-Route" in response.data

def test_404_handling(client):
    """Test the URL mapping intercept functionality."""
    response = client.get("/random-invalid-url-sweep")
    assert response.status_code == 404
    assert response.is_json
    assert "Resource not found" in response.get_json()["error"]

def test_invalid_content_type(client):
    """Test invalid HTTP payloads format rejection limits."""
    response = client.post("/process", data="raw string here")
    assert response.status_code == 415
    assert response.is_json

def test_process_no_message(client):
    """Test robust API bounds regarding parameter faults."""
    with patch("app.api_key", "dummy_key"):
        with patch("app.model", MagicMock()):
            response = client.post("/process", json={})
            assert response.status_code == 400
            data = response.get_json()
            assert "explicitly provided" in data["error"]

def test_process_missing_api_key(client):
    """Test API configuration interception."""
    with patch("app.api_key", None):
        response = client.post("/process", json={"message": "Valid string"})
        assert response.status_code == 500
        data = response.get_json()
        assert "Gemini Key Missing" in data["error"]

@patch("app.model")
def test_process_sanitizes_xss(mock_model_global, client):
    """Test XSS string mappings evaluating the HTML library escaping paths."""
    mock_result = MagicMock()
    mock_result.text = '{"severity": "High", "intent": "Rescue", "location_summary": "123", "actionable_recommendation": "Step", "priority_level": 5}'
    mock_model_global.generate_content.return_value = mock_result

    with patch("app.api_key", "dummy_key"):
        xss_payload = "<script>alert('pwned')</script> I need help!"
        response = client.post("/process", json={"message": xss_payload})
        assert response.status_code == 200
        escaped_payload = html.escape(xss_payload)
        mock_model_global.generate_content.assert_called_once_with(escaped_payload)

@patch("app.model")
def test_process_success(mock_model_global, client):
    """Test end to end data restructuring."""
    mock_result = MagicMock()
    mock_result.text = '{"severity": "High", "intent": "Rescue", "location_summary": "123 Elm St", "actionable_recommendation": "Dispatch swift water boat.", "priority_level": 5}'
    mock_model_global.generate_content.return_value = mock_result

    with patch("app.api_key", "dummy_key"):
        with patch("app.storage_client", MagicMock()):
            response = client.post("/process", json={"message": "We are drowning at 123 Elm St!"})
            assert response.status_code == 200
            data = response.get_json()
            assert data["severity"] == "High"
            assert data["priority_level"] == 5

@patch("app.model")
def test_process_exception_handler(mock_model_global, client):
    """Test explicit global engine errors bypassing standard 500 routines."""
    mock_model_global.generate_content.side_effect = Exception("System Crash")
    with patch("app.api_key", "dummy_key"):
        response = client.post("/process", json={"message": "Crash me"})
        assert response.status_code == 500

def test_raw_500(client):
    """Trigger the global 500 error handler directly to ensure perfect coverage parsing."""
    from app import internal_server_error
    with client.application.app_context():
        response, code = internal_server_error(Exception("Framework Crash Injection"))
        assert code == 500
