"""
Main execution controller mapping emergency NLP processing.
Routes across Vertex/GenAI, Storage, Logging, Pub/Sub, and Firestore.
"""

import os
import json
import html
import uuid
import logging
from typing import Tuple, Any, Optional

from flask import Flask, request, jsonify, render_template, Response
import google.generativeai as genai
from dotenv import load_dotenv

from google.cloud import logging as cloud_logging
from google.cloud import storage
from google.cloud import error_reporting
from google.cloud import pubsub_v1
import firebase_admin
from firebase_admin import firestore

load_dotenv()
app = Flask(__name__)

# Native Security Parameters Setup
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True

api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
gcp_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "fourth-arena-491605-j1")
bucket_name: str = f"staging.{gcp_project}.appspot.com"
topic_name: str = f"projects/{gcp_project}/topics/disaster-signals-feed"

gcp_logger = logging.getLogger(__name__)

# ==========================================
# HELPER ABSTRACTIONS (Cyclomatic Reduction)
# ==========================================


def initialize_gcp_clients() -> Tuple[Any, Any, Any, Any]:
    """Helper mapping all live Google services dynamically."""
    try:
        logging_client = cloud_logging.Client()
        logging_client.setup_logging()

        st_client = storage.Client()
        err_client = error_reporting.Client()
        pb_client = pubsub_v1.PublisherClient()

        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        db_ref = firestore.client()
        return st_client, err_client, pb_client, db_ref
    except Exception:
        gcp_logger.warning("GCP Native SDKs operating in stub mode.")
        return None, None, None, None


def initialize_vertex_ai() -> Any:
    """Helper mapping GenAI bindings natively."""
    try:
        if api_key:
            genai.configure(api_key=api_key)
            gen_cfg = {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            }
            system_instruction = (
                "You are an incident triage assistant. "
                "Read unstructured signals to extract: "
                "severity (Low, Medium, High, Critical), "
                "intent (Rescue, Medical, Information, Supplies, Other), "
                "location_summary, actionable_recommendation, "
                "and priority_level (1 to 5). "
                "Respond ONLY with valid JSON mapping."
            )
            return genai.GenerativeModel(
                "gemini-flash-latest",
                generation_config=gen_cfg,
                system_instruction=system_instruction,
            )
    except Exception:
        return None
    return None


clients = initialize_gcp_clients()
storage_client, error_client, pubsub_client, db_client = clients
model = initialize_vertex_ai()


def persist_to_ecosystem(
    result_json: dict, payload_string: str, signal_id: str
) -> None:
    """Helper orchestrating NoSQL and Blob persistence bounds."""
    try:
        if storage_client:
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(f"disaster-signals/{signal_id}.json")
            blob.upload_from_string(
                data=payload_string, content_type="application/json"
            )
        if pubsub_client:
            encoded_payload = payload_string.encode("utf-8")
            pubsub_client.publish(topic_name, encoded_payload)
        if db_client:
            collection = db_client.collection("triage_incidents")
            doc_ref = collection.document(signal_id)
            doc_ref.set(result_json)
        gcp_logger.info("Universal GCP Database Pipeline complete.")
    except Exception as bucket_err:
        gcp_logger.error(f"Ecosystem bypass fault: {str(bucket_err)}")


# ==========================================
# ROUTING CONTROLLERS
# ==========================================


@app.after_request
def add_security_headers(response: Response) -> Response:
    """Inject native strict OWASP HTTP Security boundary headers."""
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline' "
        "https://fonts.googleapis.com https://fonts.gstatic.com data:;"
    )
    return response


@app.errorhandler(404)
def resource_not_found(e: Exception) -> Tuple[Any, int]:
    """Gracefully catch 404 URL sweeps mapping to structured JSON."""
    gcp_logger.warning("404 Framework evaluation sweep blocked.")
    return jsonify({"error": "Resource not found."}), 404


@app.errorhandler(500)
def internal_server_error(e: Exception) -> Tuple[Any, int]:
    """Gracefully trace 500 runtime framework faults to Stackdriver."""
    gcp_logger.error(f"500 Internal Fault Boundary triggers: {str(e)}")
    if error_client:
        error_client.report_exception()
    return jsonify({"error": "Internal server fault intercepted."}), 500


@app.route("/")
def index() -> str:
    """Serve the DOM UI index structure strictly."""
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process() -> Tuple[Any, int]:
    """API Interface validating NLP formatting boundaries over text."""
    gcp_logger.info("Signal generation request initiated.")

    if not api_key or model is None:
        return jsonify({"error": "Gemini Key Missing"}), 500
    if not request.is_json:
        return jsonify({"error": "Invalid Content-Type payload"}), 415

    data = request.json
    if not data or not data.get("message"):
        err_msg = {"error": "No message parameter explicitly provided"}
        return jsonify(err_msg), 400

    safe_message = html.escape(str(data.get("message")).strip())

    try:
        response = model.generate_content(safe_message)
        result_json = json.loads(response.text)
        signal_id = f"signal_{uuid.uuid4().hex}"

        persist_to_ecosystem(result_json, json.dumps(result_json), signal_id)

        return jsonify(result_json), 200

    except Exception as e:
        gcp_logger.error(f"Generative Process Engine Fault: {str(e)}")
        if error_client:
            error_client.report(f"Generative Fault Intercepted: {str(e)}")
        return jsonify({"error": str(e)}), 500


def main() -> None:
    """System entrypoint map initiating host interfaces."""
    host_addr = os.environ.get("HOST", "0.0.0.0")
    run_port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host=host_addr, port=run_port)


if __name__ == "__main__":
    main()
