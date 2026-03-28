import os
import json
import html
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Tuple, Any

# Load environment configuration safely
load_dotenv()

app = Flask(__name__)

# Configure Gemini globally to restrict repeated authentication sweeps
api_key = os.getenv("GEMINI_API_KEY")

generation_config = {
  "temperature": 0.2, # Exactingly low temperature constraints
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 1024,
  "response_mime_type": "application/json",
}

SYSTEM_INSTRUCTION = """
You are a disaster incident triage assistant. Your job is to read unstructured, messy text signals 
from a crisis zone and instantly convert them into a structured JSON payload for emergency dispatchers.

Extract the following from the input:
- "severity": "Low", "Medium", "High", or "Critical"
- "intent": "Rescue", "Medical", "Information", "Supplies", or "Other"
- "location_summary": A brief detail of where this is happening. Say "Unknown" if not mentioned.
- "actionable_recommendation": One specific immediate step a dispatcher or responder should take based on the input.
- "priority_level": Integer from 1 (lowest) to 5 (highest life-threatening).

Respond ONLY with valid JSON matching these exact keys. Do not include markdown formatting.
"""

# EFFICIENCY OPTIMIZATION: Initialize the GenerativeModel *exactly once* at startup.
# Loading large model bindings heavily spikes runtime inside individual API routes.
try:
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=generation_config,
            system_instruction=SYSTEM_INSTRUCTION
        )
    else:
        model = None
except Exception as e:
    # Failsafe for missing API configurations
    model = None


@app.route("/")
def index() -> str:
    """
    Serve the core glassmorphism triage UI layout.
    
    Returns:
        str: Fully rendered HTML string payload.
    """
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process() -> Tuple[Any, int]:
    """
    API Interface bridging raw unstructured UI text signals directly 
    to the Gemini execution model. Includes strict security sanitization.
    
    Returns:
        Tuple containing a flask.Response JSON object and HTTP Status Code.
    """
    # 1. Configuration Validation
    if not api_key or model is None:
        return jsonify({"error": "Gemini API key not configured. Please add GEMINI_API_KEY to your environment."}), 500

    # 2. Input Integrity Checks
    data = request.json
    if not data:
         return jsonify({"error": "Invalid JSON format provided."}), 400
         
    raw_message = data.get("message")
    if not raw_message or not str(raw_message).strip():
        return jsonify({"error": "No message provided."}), 400

    # 3. SECURITY: Strict Input Sanitization to prevent Persistent XSS execution
    safe_message = html.escape(str(raw_message).strip())

    # 4. Model Generation logic execution
    try:
        response = model.generate_content(safe_message)
        result_str = response.text
        
        # Rigorous schema decoding verifying JSON safety
        try:
             result_json = json.loads(result_str)
        except json.JSONDecodeError:
             return jsonify({"error": "Failed to rigidly parse structured JSON from the model layer.", "raw": result_str}), 500
             
        return jsonify(result_json), 200

    except Exception as e:
        return jsonify({"error": f"Model execution unhandled exception: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
