import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from app import create_app
from app.config import TestingConfig
from app.services import TriageService
from app.exceptions import TriageAPIError, VertexGenerationError

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Mock GCP clients during app creation
    with patch("google.cloud.error_reporting.Client"):
        app = create_app(TestingConfig)
        yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def triage_service():
    """A triage service instance with mocked GCP clients."""
    with patch("google.cloud.storage.Client"), \
         patch("google.cloud.pubsub_v1.PublisherClient"), \
         patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.firestore.client"):
        return TriageService()

def test_index_route(client):
    """Test the root index route renders correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"<!DOCTYPE html>" in response.data

def test_404_handler(client):
    """Test the custom 404 JSON handler."""
    response = client.get("/invalid-route-123")
    assert response.status_code == 404
    assert response.json == {"error": "Resource not found."}

def test_process_no_json(client):
    """Test /process endpoint with non-JSON payload."""
    response = client.post("/process", data="not json")
    assert response.status_code == 415

def test_process_empty_json(client):
    """Test /process with empty JSON."""
    response = client.post("/process", json={})
    assert response.status_code == 400

def test_process_missing_message(client):
    """Test /process with missing 'message' key."""
    response = client.post("/process", json={"foo": "bar"})
    assert response.status_code == 400

@patch("app.routes.triage_engine.process_signal")
def test_process_success(mock_process, client):
    """Test successful signal processing."""
    mock_process.return_value = {"severity": "High"}
    response = client.post("/process", json={"message": "Help!"})
    assert response.status_code == 200
    assert response.json == {"severity": "High"}

@patch("app.routes.triage_engine.process_signal")
def test_process_api_error(mock_process, client):
    """Test custom API error handling."""
    mock_process.side_effect = TriageAPIError("Bad request", 400)
    response = client.post("/process", json={"message": "Fault"})
    assert response.status_code == 400
    assert response.json == {"error": "Bad request"}

@patch("app.routes.triage_engine.process_signal")
def test_process_general_error(mock_process, client):
    """Test general exception handling."""
    mock_process.side_effect = Exception("System crash")
    response = client.post("/process", json={"message": "Crash"})
    assert response.status_code == 500
    assert "error" in response.json

def test_triage_service_init_no_key():
    """Test service initialization when API key is missing."""
    with patch("app.services.Config.GEMINI_API_KEY", None), \
         patch("google.generativeai.configure") as mock_config, \
         patch("google.cloud.storage.Client"), \
         patch("google.cloud.pubsub_v1.PublisherClient"), \
         patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.firestore.client"):
        service = TriageService()
        assert service.model is None
        mock_config.assert_not_called()

def test_triage_service_init_exception(triage_service):
    """Test service initialization when configure throws."""
    with patch("app.services.Config.GEMINI_API_KEY", "key"), \
         patch("google.generativeai.configure", side_effect=Exception("fail")), \
         patch("app.services.logger.error") as mock_log:
        triage_service._initialize_vertex_ai()
        mock_log.assert_called_once()

def test_triage_service_select_model_fallback(triage_service):
    """Test the model selection fallback mechanism."""
    with patch("google.generativeai.GenerativeModel") as mock_model:
        # First call fails, second succeeds
        mock_model.side_effect = [Exception("Credits exhausted"), MagicMock()]
        triage_service._select_model()
        assert mock_model.call_count == 2

def test_security_headers(client):
    """Ensure security headers are present on all responses."""
    response = client.get("/")
    assert "Strict-Transport-Security" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Content-Security-Policy" in response.headers

def test_structured_logging_config():
    """Verify structured logging configuration doesn't crash."""
    from app import configure_structured_logging
    # Should not raise
    configure_structured_logging()

def test_create_app_with_error_client():
    """Test app creation when error reporting client is available."""
    with patch("google.cloud.error_reporting.Client", side_effect=Exception("Disabled")):
        app = create_app(TestingConfig)
        assert app is not None

def test_internal_server_error_reporting(app):
    """Test error reporting during 500 handler."""
    with app.test_request_context():
        # Inject mock client
        with patch("app.GCP_ERROR_CLIENT") as mock_client:
            from app import internal_server_error
            res, code = internal_server_error(Exception("Test"))
            assert code == 500
            mock_client.report_exception.assert_called_once()

def test_resource_not_found_handler(app):
    """Test the resource not found handler directly."""
    from app import resource_not_found
    with app.test_request_context():
        res, code = resource_not_found(Exception("404"))
        assert code == 404

def test_exceptions_models():
    """Test exception class initialization."""
    err = TriageAPIError("msg", 401)
    assert err.status_code == 401
    
    v_err = VertexGenerationError("gen_fail", 500)
    assert v_err.status_code == 500

def test_triage_service_process_no_model(triage_service):
    """Test error when processing signal without an initialized model."""
    triage_service.model = None
    with pytest.raises(VertexGenerationError):
        triage_service.process_signal("test")

def test_triage_service_process_success(triage_service):
    """Test service-level signal processing success."""
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = '{"severity": "Low"}'
    triage_service.model = mock_model
    
    with patch.object(triage_service, "_persist_to_ecosystem") as mock_persist:
        result = triage_service.process_signal("Safe")
        assert result == {"severity": "Low"}
        mock_persist.assert_called_once()

def test_persist_to_ecosystem_clients_present(triage_service):
    """Test persistence logic when all GCP clients are enabled."""
    triage_service.st_client = MagicMock()
    triage_service.pb_client = MagicMock()
    triage_service.db_client = MagicMock()
    
    triage_service._persist_to_ecosystem({"test": 1}, "{}", "sid123")
    triage_service.st_client.bucket.assert_called_once()
    triage_service.pb_client.publish.assert_called_once()
    triage_service.db_client.collection.assert_called_once()

def test_persist_to_ecosystem_exception(triage_service):
    """Test that persistence exceptions are logged but not re-raised."""
    triage_service.st_client = MagicMock()
    triage_service.st_client.bucket.side_effect = Exception("Storage death")
    
    # Should not raise
    triage_service._persist_to_ecosystem({"test": 1}, "{}", "sid123")

def test_triage_service_process_exception(triage_service):
    """Test service-level exception handling during generation."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("Vertex failure")
    triage_service.model = mock_model
    with pytest.raises(VertexGenerationError):
        triage_service.process_signal("Crash")
