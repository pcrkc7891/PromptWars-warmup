# ResQ-Route: Disaster Signal Aggregator

## 🏆 PromptWars Hackathon - main Phase Submission

* **Challenge Vertical:** Emergency Response / Disaster Relief
* **App Name:** **ResQ-Route**

## 💡 The Problem & Logic
During massive natural disasters (like hurricanes or floods), 100/108/112 dispatch centers are overwhelmed. Chaos ensues as victims post frantic, unstructured cries for help across various channels (texts, social media, emergency lines). These inputs are incredibly messy—containing slang, typos, panic, and fragmented location data.

**The Approach:**
ResQ-Route acts as the ultimate bridge. It takes raw, unstructured "messy" human intent signals and immediately structuralizes them into clean, verified JSON payloads. It determines the `Severity` of the incident, the core `Intent` (Is it a medical emergency or just a request for info?), extracts the `Location`, and provides an `Immediate Life-Saving Action` for emergency dispatchers.

## 🚀 How It Works
1. **The Input:** Dispatchers or an automated pipeline feed raw text strings into the ResQ-Route dashboard.
2. **The Gemini Bridge:** The backend leverages the `Google Gemini 1.5 Flash` API. Using strict system instructions and `response_mime_type="application/json"`, Gemini uses its advanced reasoning to parse the chaotic text and extract precise data points.
3. **The Output:** It guarantees a perfectly formatted, structured web dashboard visualization and raw JSON response that maps priority levels from 1 to 5. This allows dispatchers to instantly deploy units to the most critical life-threatening, situations first.

### Assumptions Made
* The input language is primarily text-based for this lightweight iteration.
* The deployment environment has `GEMINI_API_KEY` configured securely in the environment variables, ensuring the key is not exposed.
* Dispatchers require < 2 seconds of latency, which is why we utilized the extremely fast `Gemini 1.5 Flash` model.

## 🛠️ Google Services Used
* **Google Gemini API** (`gemini-1.5-flash`)
* **Google Cloud Platform App Engine** (Deployment ready via the included `app.yaml`)

## 💻 Tech Stack
* **Backend:** Python + Flask
* **Frontend:** Vanilla HTML/JS/CSS (Zero bloat, extremely fast, repo size well under 1 MB limit)
* **Testing:** `pytest` unit testing suite included to ensure structural reliability.

## 🏃‍♂️ Running Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Export your Gemini API key:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

3. Run the application:
```bash
python app.py
```
Open your browser to `http://localhost:8080`
