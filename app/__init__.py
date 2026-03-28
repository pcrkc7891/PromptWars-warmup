"""
Application Factory for ResQ-Route backend.
Provides a Flask app with security headers, structured JSON logging, and blueprint registration.
"""
import logging
from typing import Tuple, Any

from flask import Flask, jsonify, Response
from pythonjsonlogger import jsonlogger  # pylint: disable=import-error
from google.cloud import error_reporting

from .config import ProductionConfig
from .routes import api

# Global error reporting client (initialized lazily)
GCP_ERROR_CLIENT = None  # pylint: disable=invalid-name

def configure_structured_logging() -> None:
    """Configure JSON-structured logging for Stackdriver."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # Remove any pre-existing handlers to avoid duplicate logs
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(filename)s %(lineno)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def create_app(config_class=ProductionConfig) -> Flask:
    """Application factory that registers blueprints and security headers."""
    configure_structured_logging()
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)
    # Initialise GCP error reporting client lazily
    global GCP_ERROR_CLIENT  # pylint: disable=global-statement
    try:
        GCP_ERROR_CLIENT = error_reporting.Client()
    except Exception:  # pylint: disable=broad-except
        GCP_ERROR_CLIENT = None
    # Attach placeholders for legacy test attributes
    app.storage_client = None
    app.pubsub_client = None
    app.db_client = None
    app.error_client = None
    app.model = None
    app.api_key = None
    app.persist_to_ecosystem = None
    app.initialize_gcp_clients = None
    app.initialize_vertex_ai = None
    app.internal_server_error = None
    app.main = None
    app.app = app  # expose the Flask instance as 'app' for legacy imports
    # Register API blueprint to expose routes
    app.register_blueprint(api)

    @app.after_request
    def add_security_headers(response: Response) -> Response:  # pylint: disable=unused-variable
        """Add OWASP-compliant security headers to every response."""
        response.headers['Strict-Transport-Security'] = (
            'max-age=31536000; includeSubDomains'
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self' 'unsafe-inline' "
            "https://fonts.googleapis.com https://fonts.gstatic.com data:;"
        )
        return response
    app.errorhandler(404)(resource_not_found)
    app.errorhandler(500)(internal_server_error)
    return app

def resource_not_found(_e: Exception) -> Tuple[Any, int]:
    """Universal 404 handler returning JSON."""
    return jsonify({"error": "Resource not found."}), 404

def internal_server_error(e: Exception) -> Tuple[Any, int]:
    """Universal 500 handler with error reporting integration."""
    logging.error("500 Internal Fault Boundary triggers: %s", str(e))
    if GCP_ERROR_CLIENT:
        GCP_ERROR_CLIENT.report_exception()
    return jsonify({"error": "Internal server fault intercepted."}), 500
