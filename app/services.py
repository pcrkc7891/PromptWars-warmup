"""
Core Business Service Logic mapping GCP natively separated from HTTP handlers.
"""
import json
import uuid
import logging
from typing import Any, Optional


import google.generativeai as genai
from google.cloud import storage, pubsub_v1
import firebase_admin
from firebase_admin import firestore

from .exceptions import VertexGenerationError
from .config import Config

logger = logging.getLogger(__name__)


class TriageService:  # pylint: disable=too-few-public-methods
    """Decoupled Service Class structurally isolating all Backend Cloud Architecture."""

    def __init__(self) -> None:
        """Initialize explicit native GCP clients securely."""
        self.st_client: Optional[storage.Client] = None
        self.pb_client: Optional[pubsub_v1.PublisherClient] = None
        self.db_client: Optional[Any] = None
        self.model: Optional[Any] = None
        self._gen_cfg = {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_output_tokens": 1024,
            "response_mime_type": "application/json",
        }
        self._instruction = (
            "You are an incident triage assistant. Read unstructured signals "
            "to extract: severity (Low, Medium, High, Critical), "
            "intent (Rescue, Medical, Information, Supplies, Other), "
            "location_summary, actionable_recommendation, "
            "and priority_level (1 to 5). Respond strictly with valid JSON."
        )
        self.model = None
        self._initialize_gcp_clients()
        self._initialize_vertex_ai()


    def _initialize_gcp_clients(self) -> None:
        """Bind underlying Pub/Sub, Storage, and NoSQL SDK boundaries natively."""
        try:
            self.st_client = storage.Client()
            self.pb_client = pubsub_v1.PublisherClient()
            if not firebase_admin._apps:  # pylint: disable=protected-access
                firebase_admin.initialize_app()
            self.db_client = firestore.client()
            logger.info("Universal GCP Cloud Clients natively resolved.")
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("GCP SDK failed allocation natively: %s", str(e))

    def _initialize_vertex_ai(self) -> None:
        """Configure GenAI with API Key and select the appropriate model."""
        try:
            if Config.GEMINI_API_KEY:
                genai.configure(api_key=Config.GEMINI_API_KEY)
                self.model = self._select_model()
            else:
                logger.warning("GEMINI_API_KEY is missing. Model not initialized.")
        except Exception as general_err:  # pylint: disable=broad-except
            logger.error("Generative Service Fault Interface Trap: %s", str(general_err))

    def _select_model(self):
        """Return a GenerativeModel.
        If the primary model fails (e.g. credits), fall back to gemini-pro.
        """
        try:
            return genai.GenerativeModel(
                "gemini-flash-latest",
                generation_config=self._gen_cfg,
                system_instruction=self._instruction,
            )
        except Exception:  # pragma: no cover # pylint: disable=broad-except
            logger.warning("Primary Gemini model unavailable, falling back to gemini-pro")
            return genai.GenerativeModel(
                "gemini-pro",
                generation_config=self._gen_cfg,
                system_instruction=self._instruction,
            )

    def process_signal(self, raw_message: str) -> dict:
        """Handle exact core generation and structured saving business boundaries."""
        if not self.model:
            raise VertexGenerationError("GenAI Model not natively mapped.", 500)

        try:
            # 1. Structure the Signal via LLM
            response = self.model.generate_content(raw_message)
            result_payload = json.loads(response.text)
            # 2. Append internal identification map natively
            signal_id = f"signal_{uuid.uuid4().hex}"

            # 3. Securely transmit structured bounds across Ecosystem
            self._persist_to_ecosystem(
                result_payload,
                json.dumps(result_payload),
                signal_id
            )
            return result_payload

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Signal Structuring boundary trace failed natively: %s", str(e))
            raise VertexGenerationError(f"API processing fault: {str(e)}", 500) from e

    def _persist_to_ecosystem(self, data: dict, raw_json: str, sid: str) -> None:
        """Map internal GCP save mechanics securely."""
        try:
            # Cloud Storage
            if self.st_client:
                bucket = self.st_client.bucket(Config.BUCKET_NAME)
                bucket.blob(f"disaster-signals/{sid}.json").upload_from_string(
                    data=raw_json, content_type="application/json"
                )
            # Pub/Sub Streaming
            if self.pb_client:
                self.pb_client.publish(Config.TOPIC_NAME, raw_json.encode("utf-8"))
            # Firestore Realtime Collection
            if self.db_client:
                self.db_client.collection("triage_incidents").document(sid).set(data)
            logger.info("Signal %s internally stored natively across the ecosystem.", sid)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Ecosystem storage pipeline natively dropped variables: %s", str(e))
