import os
import json
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure Gemini. In a production/hackathon execution environment, Ensure GEMINI_API_KEY is defined.
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# System instruction to enforce JSON schema and behavioral logic
generation_config = {
  "temperature": 0.2, # Low temperature for reliable, logical structuring
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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    if not api_key:
        return jsonify({"error": "Gemini API key not configured. Please add GEMINI_API_KEY to your environment."}), 500

    data = request.json
    message = data.get("message")

    if not message:
        return jsonify({"error": "No message provided."}), 400

    try:
        # Utilize gemini-flash-latest from the user's available model list
        model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            generation_config=generation_config,
            system_instruction=SYSTEM_INSTRUCTION
        )

        response = model.generate_content(message)
        
        # The response should be pure JSON due to response_mime_type
        result_str = response.text
        
        try:
             result_json = json.loads(result_str)
        except json.JSONDecodeError:
             return jsonify({"error": "Failed to parse JSON from Gemini.", "raw": result_str}), 500
             
        return jsonify(result_json)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
