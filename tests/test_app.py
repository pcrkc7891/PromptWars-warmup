import pytest
import runpy
from unittest.mock import patch, MagicMock

# Crucial: Mock intensive GCP instantiations BEFORE app loop imports.
with patch("google.cloud.logging.Client"), patch(  # noqa: E501
    "google.cloud.storage.Client"
), patch("google.cloud.error_reporting.Client"), patch(
    "google.cloud.pubsub_v1.PublisherClient"
), patch(
    "firebase_admin.initialize_app"
), patch(
    "firebase_admin.firestore.client"
):
    import app


@pytest.fixture
def client():
    app.app.config["TESTING"] = True
    with app.app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_404_handling(client):
    response = client.get("/random-invalid-url-sweep")
    assert response.status_code == 404


def test_invalid_content_type(client):
    response = client.post("/process", data="raw string here")
    assert response.status_code == 415


def test_process_no_message(client):
    with patch("app.api_key", "dummy_key"):
        with patch("app.model", MagicMock()):
            response = client.post("/process", json={})
            assert response.status_code == 400


def test_process_missing_api_key(client):
    with patch("app.api_key", None):
        response = client.post("/process", json={"message": "Valid string"})
        assert response.status_code == 500


@patch("app.model")
def test_process_success(mock_model_global, client):
    mock_result = MagicMock()
    mock_result.text = '{"severity": "High", "intent": "Rescue", "location_summary": "123 Elm St", "actionable_recommendation": "Step", "priority_level": 5}'  # noqa: E501
    mock_model_global.generate_content.return_value = mock_result
    with patch("app.api_key", "dummy_key"):
        with patch("app.persist_to_ecosystem", MagicMock()):
            response = client.post(
                "/process", json={"message": "We are drowning at 123 Elm St!"}
            )
            assert response.status_code == 200


@patch("app.model")
def test_process_exception_handler(mock_model_global, client):
    mock_model_global.generate_content.side_effect = Exception("System Crash")
    with patch("app.api_key", "dummy_key"):
        with patch("app.error_client", MagicMock()) as err_client:
            app.error_client = err_client
            response = client.post("/process", json={"message": "Crash me"})
            assert response.status_code == 500
            err_client.report.assert_called_once()


def test_raw_500(client):
    with patch("app.error_client", MagicMock()) as err_client:
        with client.application.app_context():
            response, code = app.internal_server_error(
                Exception("Framework Crash Injection")
            )
            assert code == 500
            err_client.report_exception.assert_called_once()


def test_initialize_gcp_clients_exception():
    with patch(
        "google.cloud.storage.Client",
        side_effect=Exception("Initialization Fault"),
    ):
        res = app.initialize_gcp_clients()
        assert res == (None, None, None, None)


def test_initialize_vertex_ai_exception():
    with patch(
        "google.generativeai.configure",
        side_effect=Exception("Vertex configuration crash"),
    ):
        with patch("app.api_key", "fake-key"):
            res = app.initialize_vertex_ai()
            assert res is None


def test_initialize_vertex_ai_no_key():
    with patch("app.api_key", None):
        res = app.initialize_vertex_ai()
        assert res is None


def test_persist_to_ecosystem_success():
    mock_storage = MagicMock()
    mock_pubsub = MagicMock()
    mock_db = MagicMock()
    app.storage_client = mock_storage
    app.pubsub_client = mock_pubsub
    app.db_client = mock_db
    app.persist_to_ecosystem({"data": 1}, '{"data":1}', "test_id")
    mock_storage.bucket().blob().upload_from_string.assert_called_once()
    mock_pubsub.publish.assert_called_once()
    mock_db.collection().document().set.assert_called_once()


def test_persist_to_ecosystem_exception():
    mock_storage = MagicMock()
    mock_storage.bucket.side_effect = Exception("Storage Fault")
    app.storage_client = mock_storage
    app.pubsub_client = None
    app.db_client = None
    app.persist_to_ecosystem({"data": 1}, '{"data": 1}', "test_id")


@patch("flask.Flask.run")
def test_main_execution_engine(mock_run):
    app.main()
    mock_run.assert_called_once()


@patch("flask.Flask.run")
def test_name_main(mock_run):
    # This invokes app.py explicitly evaluating the OS global hooks natively resolving 100%  # noqa: E501
    runpy.run_module("app", run_name="__main__")
    mock_run.assert_called_once()
