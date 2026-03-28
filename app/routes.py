"""
Strict HTTP API Routing logic mapping securely to the Frontend bounds.
"""
import html
import logging
from typing import Tuple, Any

from flask import Blueprint, request, jsonify, render_template

from .services import TriageService
from .exceptions import TriageAPIError

api = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

# Single service instantiation safely isolated.
triage_engine = TriageService()

@api.route("/")
def index() -> str:
    """Serve structured Native DOM architecture natively."""
    return render_template("index.html")

@api.route("/process", methods=["POST"])
def process() -> Tuple[Any, int]:
    """Intercept and structurally validate GenAI Triage operations centrally."""
    logger.info("Signal generation structural request initiated.")

    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type payload"}), 415

    data = request.json
    if not data or not data.get("message"):
        error_msg = {"error": "No message parameter explicitly provided"}
        return jsonify(error_msg), 400

    # Sanitize inputs explicitly
    safe_message = html.escape(str(data.get("message")).strip())

    try:
        resultado = triage_engine.process_signal(safe_message)
        return jsonify(resultado), 200

    except TriageAPIError as custom_err:
        logger.warning("Business Service natively trapped error: %s", custom_err.message)
        return jsonify({"error": custom_err.message}), custom_err.status_code

    except Exception as general_err:  # pylint: disable=broad-except
        logger.error("Generative Service Fault Interface Trap: %s", str(general_err))
        return jsonify({"error": "Internal Framework Fault intercepted."}), 500
