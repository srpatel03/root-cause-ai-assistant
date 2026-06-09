# ⚙️ Root Cause AI Assistant

An interactive, conversational Operational Excellence AI Assistant designed to guide team members through a rigorous process review and clinical safety "5 Whys" analysis. Built with Python, Streamlit, LangChain, and Google Gemini models.

---

## 🚀 Key Features

* **📋 Left Sidebar Progress Tracker**: A dynamic, vertical step-by-step visual stepper that outlines the current investigation phase, showing live validated subtitles and step statuses (Completed, Active, Skipped, Pending).
* **💬 Conversational "5 Whys" Facilitation**: Guides you through identifying immediate, intermediate, and systemic process failure causes, automatically intercepting individual human error or blame.
* **⚠️ Logic Critique Guardrails**: Prevents individual blame traps, prompting users to focus on process design, workflow design, and systemic safeguards rather than human mistakes.
* **📝 A3 Project Charter Blueprint**: Generates a unified 2x2 grid representing a formal Lean A3 Project Charter (Problem Statement, RCA Summary, Proposed Countermeasures, Key Success Metrics) once the root cause is established.
* **💬 A3 Charter Refinement Copilot**: An interactive dialogue chat block that lets you refine, discuss, and adjust targets or metrics in the charter (e.g. asking *"What should my wait times be?"* to get consulting advice, or stating *"Set success metric target to less than 8 minutes"* to modify the charter dynamically).
* **🖨️ High-Contrast Print Overrides**: Fully customized print styles (`@media print`) that hide interactive inputs, sidebar trackers, and chat logs, compiling only the timeline and the 2x2 charter grid for clean paper handouts or PDF exports.

---

## 🛠️ Installation & Local Setup

This project uses [uv](https://github.com/astral-sh/uv) for fast Python dependency management.

### Prerequisites
- Python 3.10+ (Python 3.13 recommended)
- A Google Gemini API Key

### Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/srpatel03/root-cause-ai-assistant.git
   cd root-cause-ai-assistant
   ```

2. **Configure Environment Variables**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` in your editor and add your actual API key:
   ```env
   GOOGLE_API_KEY=your-actual-gemini-key
   ```

3. **Install Dependencies & Launch the App**:
   Run the Streamlit server using `uv`:
   ```bash
   uv run streamlit run app.py
   ```
   The application will automatically open in your browser at `http://localhost:8501`.

---

## ☁️ Deployment

You can deploy this application for free using **Streamlit Community Cloud**:

1. Push your repository to GitHub (ensure `.env` is omitted and ignored by [.gitignore](.gitignore)).
2. Go to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
3. Click **New app**, select this repository, and set the entry file to `app.py`.
4. Go to **Advanced settings...** -> **Secrets** and add your Google Gemini API key:
   ```toml
   GOOGLE_API_KEY = "your-actual-gemini-key"
   ```
5. Click **Deploy!**
