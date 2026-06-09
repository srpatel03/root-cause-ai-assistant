import streamlit as st
import time
import os
from llm import get_facilitator_response, generate_a3_charter, refine_a3_charter

def clean_html(html: str) -> str:
    """Removes leading spaces from each line in a multi-line HTML string to prevent Markdown code block triggers."""
    return "\n".join(line.strip() for line in html.strip().split("\n"))

# Load local environment variables from .env if present
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    key, val = parts
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Page Configuration (Universal healthcare icon, standard title, collapsed sidebar by default)
st.set_page_config(
    page_title="Root Cause AI Assistant",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session States
if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Welcome to the Root Cause AI Assistant. To begin a rigorous Sentinel Event review or clinical process investigation, please describe the patient safety event or operational failure.<br><br><i>Example: 'A clinician pulled and administered the wrong medication (Vecuronium instead of Versed) from the Pyxis cabinet under an override.'</i>",
        "why_num": 0,
        "is_critique": False
    }]
if "session_started" not in st.session_state:
    st.session_state.session_started = False
if "charter_generated" not in st.session_state:
    st.session_state.charter_generated = False
if "why_count" not in st.session_state:
    st.session_state.why_count = 0
if "charter_data" not in st.session_state:
    st.session_state.charter_data = None
if "validated_answers" not in st.session_state:
    st.session_state.validated_answers = []
if "initial_problem" not in st.session_state:
    st.session_state.initial_problem = ""
if "session_concluded" not in st.session_state:
    st.session_state.session_concluded = False
if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "chat"
if "refinement_messages" not in st.session_state:
    st.session_state.refinement_messages = []

# Retrieve API Key from Environment
api_key = os.environ.get("GOOGLE_API_KEY")

# Sidebar Layout (collapsible, displaying vertical progress stepper)
with st.sidebar:
    st.markdown('<div class="sidebar-header">📋 Progress Tracker</div>', unsafe_allow_html=True)
    
    # Render progress stepper dynamically
    stepper_html = '<div class="stepper-container">'
    
    # Step 1: Define Problem
    s1_status = "completed" if st.session_state.initial_problem else "active"
    s1_icon = "✓" if s1_status == "completed" else "1"
    s1_subtitle = st.session_state.initial_problem if s1_status == "completed" else "State patient safety/operational event"
    stepper_html += f"""
    <div class="step-row {s1_status}">
        <div class="step-icon">{s1_icon}</div>
        <div class="step-content">
            <div class="step-title">Define Problem</div>
            <div class="step-subtitle">{s1_subtitle}</div>
        </div>
    </div>
    """
    
    # Steps 2-6: Why #1 to Why #5
    for i in range(1, 6):
        if len(st.session_state.validated_answers) >= i:
            status = "completed"
            icon = "✓"
            subtitle = st.session_state.validated_answers[i - 1]
        elif st.session_state.initial_problem and not st.session_state.session_concluded and st.session_state.why_count == i - 1:
            status = "active"
            icon = str(i + 1)
            subtitle = "Identify immediate cause" if i == 1 else "Investigating..."
        elif st.session_state.session_concluded and len(st.session_state.validated_answers) < i:
            status = "skipped"
            icon = "➖"
            subtitle = "Skipped (Root cause found)"
        else:
            status = "pending"
            icon = str(i + 1)
            subtitle = "Pending validation..."
            
        title = f"Why #{i}"
        
        stepper_html += f"""
        <div class="step-row {status}">
            <div class="step-icon">{icon}</div>
            <div class="step-content">
                <div class="step-title">{title}</div>
                <div class="step-subtitle">{subtitle}</div>
            </div>
        </div>
        """
        
    # Step 7: A3 Project Charter
    if st.session_state.charter_generated:
        s7_status = "completed"
        s7_icon = "✓"
        s7_subtitle = "Project Charter compiled!"
    elif st.session_state.session_concluded:
        s7_status = "active"
        s7_icon = "7"
        s7_subtitle = "Ready to compile action plan"
    else:
        s7_status = "pending"
        s7_icon = "7"
        s7_subtitle = "Pending session conclusion..."
        
    stepper_html += f"""
    <div class="step-row {s7_status}">
        <div class="step-icon">{s7_icon}</div>
        <div class="step-content">
            <div class="step-title">A3 Project Charter</div>
            <div class="step-subtitle">{s7_subtitle}</div>
        </div>
    </div>
    """
    
    stepper_html += '</div>'
    st.markdown(clean_html(stepper_html), unsafe_allow_html=True)

# Clean and Dynamic CSS utilizing Streamlit native theme variables
custom_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global layout & typography overrides */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Header styling */
    .app-title-container {
        padding: 1.25rem 0rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.15);
        background: linear-gradient(90deg, rgba(153, 0, 0, 0.04) 0%, rgba(153, 0, 0, 0.01) 100%);
        border-radius: 12px;
        padding-left: 20px;
    }
    .app-title {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #CC0000 0%, #990000 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .app-subtitle {
        font-size: 0.95rem;
        opacity: 0.8;
        margin-top: 0.2rem;
        font-weight: 400;
    }

    /* Sidebar customization */
    .sidebar-header {
        font-size: 1.15rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
        margin-top: 1.5rem;
        margin-bottom: 2rem;
        width: 100%;
        max-width: 100%;
        margin-left: auto;
        margin-right: auto;
    }
    
    .chat-card {
        padding: 1.25rem 1.5rem;
        border-radius: 16px;
        backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100% !important;
        box-sizing: border-box;
        position: relative;
    }
    
    .chat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(153, 0, 0, 0.08);
    }

    @keyframes pulse {
        0% { transform: scale(0.9); opacity: 0.5; }
        50% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.5; }
    }
    
    .chat-card.user {
        background: linear-gradient(135deg, rgba(55, 65, 81, 0.04) 0%, rgba(55, 65, 81, 0.08) 100%);
        border: 1px solid rgba(55, 65, 81, 0.15);
        align-self: flex-end;
        border-bottom-right-radius: 4px;
        color: var(--text-color);
    }
    
    .chat-card.assistant {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        align-self: flex-start;
        border-bottom-left-radius: 4px;
        color: var(--text-color);
    }
    
    .chat-card.assistant.latest {
        background: linear-gradient(135deg, rgba(153, 0, 0, 0.05) 0%, rgba(153, 0, 0, 0.09) 100%);
        border: 2px solid #990000;
        box-shadow: 0 8px 30px rgba(153, 0, 0, 0.12);
    }
    
    .role-badge {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .user .role-badge {
        color: #4B5563;
    }
    
    .assistant .role-badge {
        color: #990000;
    }
    
    .message-content {
        font-size: 1rem;
        line-height: 1.6;
    }

    /* General button overrides */
    .stButton, .stFormSubmitButton, [data-testid="stButton"], [data-testid="stFormSubmitButton"] {
        width: 100% !important;
    }
    .stButton > button, .stFormSubmitButton > button, [data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
        background: #990000 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        box-shadow: 0 4px 15px rgba(153, 0, 0, 0.15) !important;
    }
    
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: #B30000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(153, 0, 0, 0.25) !important;
    }
    
    .stButton > button:active, .stFormSubmitButton > button:active {
        transform: translateY(1px) !important;
    }
    
    /* Disabled states */
    .stButton > button:disabled, .stFormSubmitButton > button:disabled {
        background: #8B3A3A !important;
        color: rgba(255, 255, 255, 0.6) !important;
        border: none !important;
        box-shadow: none !important;
        transform: none !important;
        cursor: not-allowed !important;
    }

    /* Systemic Critique box */
    .critique-box {
        background-color: rgba(239, 68, 68, 0.05);
        border: 1px solid rgba(239, 68, 68, 0.20);
        border-left: 4px solid #EF4444;
        padding: 1rem;
        border-radius: 8px;
        font-size: 0.9rem;
        color: #DC2626;
        margin-top: 0.75rem;
    }
    
    /* Adapt critique box text color dynamically in dark mode */
    @media (prefers-color-scheme: dark) {
        .critique-box {
            background-color: rgba(239, 68, 68, 0.08);
            color: #FCA5A5;
            border: 1px solid rgba(239, 68, 68, 0.25);
        }
    }

    .critique-title {
        font-weight: 600;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* Phase Indicators */
    .phase-badge {
        background: rgba(153, 0, 0, 0.08);
        border: 1px solid rgba(153, 0, 0, 0.15);
        color: #990000;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-block;
        margin-top: 0.5rem;
    }

    /* Status indicator chain card */
    .chain-card {
        padding: 1.25rem;
        border-radius: 12px;
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        margin-bottom: 1.5rem;
    }

    /* Visual Timeline styling */
    .timeline {
        position: relative;
        padding: 20px 0;
        list-style: none;
        max-width: 850px;
        margin: 0 auto;
    }
    .timeline::before {
        content: " ";
        position: absolute;
        top: 0;
        bottom: 0;
        left: 40px;
        width: 3px;
        background-color: rgba(153, 0, 0, 0.2);
    }
    .timeline-item {
        position: relative;
        margin-bottom: 30px;
        padding-left: 70px;
    }
    .timeline-badge {
        position: absolute;
        top: 5px;
        left: 20px;
        width: 42px;
        height: 42px;
        border-radius: 50%;
        background-color: #990000;
        border: 3px solid var(--background-color);
        color: white !important;
        text-align: center;
        line-height: 36px;
        font-weight: 700;
        font-size: 0.85rem;
        box-shadow: 0 4px 10px rgba(153, 0, 0, 0.3);
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .timeline-panel {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        position: relative;
        box-shadow: 0 4px 20px rgba(0,0,0,0.02);
    }
    .timeline-panel-title {
        color: #990000;
        font-weight: 700;
        font-size: 1.05rem;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .timeline-panel-content {
        font-size: 1rem;
        line-height: 1.5;
        opacity: 0.9;
    }

    /* A3 2x2 Grid styling */
    .a3-grid-container {
        display: grid;
        grid-template-columns: 1fr 1fr;
        grid-auto-rows: 1fr;
        gap: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    .a3-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(153, 0, 0, 0.25);
        border-left: 5px solid #990000;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 25px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
    }
    .a3-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(153, 0, 0, 0.08);
        border-color: rgba(153, 0, 0, 0.5);
    }

    @media print {
        body, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"] {
            background-color: white !important;
            color: black !important;
        }
        [data-testid="stSidebar"], 
        header, 
        footer, 
        .stButton, 
        .stFormSubmitButton, 
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            display: none !important;
        }
        .a3-card {
            border: 2px solid #990000 !important;
            border-left: 6px solid #990000 !important;
            box-shadow: none !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
            page-break-inside: avoid !important;
        }
        .a3-card-title {
            color: #990000 !important;
            border-bottom: 1.5px solid #990000 !important;
        }
        .a3-card-body {
            color: #000000 !important;
        }
        .a3-grid-container {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            grid-auto-rows: 1fr !important;
            gap: 1rem !important;
        }
        .refinement-workspace, 
        .refinement-form-wrapper, 
        .refinement-log-header, 
        .refinement-container, 
        .refinement-card {
            display: none !important;
        }
    }
    .a3-card-title {
        color: #990000;
        font-weight: 700;
        font-size: 1.15rem;
        margin-bottom: 0.75rem;
        border-bottom: 1px solid rgba(153, 0, 0, 0.1);
        padding-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .a3-card-body {
        font-size: 0.95rem;
        line-height: 1.6;
        opacity: 0.9;
    }
    .a3-card-body ul {
        padding-left: 20px;
        margin: 0;
    }
    .a3-card-body li {
        margin-bottom: 0.5rem;
    }

    /* Banner style */
    .concluded-banner {
        background: linear-gradient(135deg, rgba(153, 0, 0, 0.06) 0%, rgba(153, 0, 0, 0.12) 100%);
        border: 1.5px dashed #990000;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 15px rgba(153, 0, 0, 0.05);
    }
    .concluded-banner-title {
        color: #990000;
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .concluded-banner-subtitle {
        font-size: 0.95rem;
        opacity: 0.85;
        margin-bottom: 1rem;
    }

    /* Sidebar progress stepper styling */
    .stepper-container {
        padding: 10px 5px;
        margin-top: 1rem;
    }
    .step-row {
        display: flex;
        align-items: flex-start;
        margin-bottom: 20px;
        position: relative;
    }
    .step-row:not(:last-child)::after {
        content: '';
        position: absolute;
        left: 14px;
        top: 30px;
        bottom: -20px;
        width: 2px;
        background-color: rgba(128, 128, 128, 0.15);
        z-index: 1;
    }
    .step-row.completed:not(:last-child)::after {
        background-color: #990000;
    }
    .step-icon {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background-color: var(--secondary-background-color);
        border: 2px solid rgba(128, 128, 128, 0.3);
        color: var(--text-color);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 700;
        z-index: 2;
        margin-right: 12px;
        transition: all 0.3s ease;
    }
    .step-row.active .step-icon {
        background-color: #990000;
        border-color: #990000;
        color: white !important;
        box-shadow: 0 0 10px rgba(153, 0, 0, 0.4);
    }
    .step-row.completed .step-icon {
        background-color: #990000;
        border-color: #990000;
        color: white !important;
    }
    .step-row.skipped .step-icon {
        background-color: rgba(128, 128, 128, 0.1);
        border-color: rgba(128, 128, 128, 0.2);
        color: rgba(128, 128, 128, 0.5) !important;
    }
    .step-content {
        flex: 1;
        padding-top: 3px;
    }
    .step-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-color);
        opacity: 0.8;
    }
    .step-row.active .step-title {
        color: #990000;
        opacity: 1;
        font-weight: 700;
    }
    .step-row.completed .step-title {
        opacity: 0.5;
        text-decoration: line-through;
    }
    .step-row.skipped .step-title {
        opacity: 0.4;
        font-style: italic;
    }
    .step-subtitle {
        font-size: 0.75rem;
        color: var(--text-color);
        opacity: 0.5;
        line-height: 1.2;
    }
    .step-row.active .step-subtitle {
        opacity: 0.8;
    }
    .step-row.skipped .step-subtitle {
        opacity: 0.3;
    }

    /* Refinement Copilot Styles */
    .refinement-container {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
        width: 100%;
        box-sizing: border-box;
    }
    .refinement-card {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-size: 0.95rem;
        line-height: 1.4;
        width: 100%;
        box-sizing: border-box;
    }
    .refinement-card.user {
        background: rgba(55, 65, 81, 0.04);
        border: 1px solid rgba(55, 65, 81, 0.1);
        border-left: 3px solid #4B5563;
        color: var(--text-color);
    }
    .refinement-card.assistant {
        background: rgba(153, 0, 0, 0.03);
        border: 1px solid rgba(153, 0, 0, 0.08);
        border-left: 3px solid #990000;
        color: var(--text-color);
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# App Header
if st.session_state.current_page == "chat":
    st.markdown(
        clean_html("""
        <div class="app-title-container">
            <h1 class="app-title">⚙️ Root Cause AI Assistant</h1>
            <div class="app-subtitle">Interactive Sentinel Event review and clinical process safety co-pilot</div>
        </div>
        """),
        unsafe_allow_html=True
    )
else:
    st.markdown(
        clean_html("""
        <div class="app-title-container">
            <h1 class="app-title">⚙️ RCA Summary & Action Plan</h1>
            <div class="app-subtitle">Visual Root Cause Chain and A3 Project Charter Blueprint</div>
        </div>
        """),
        unsafe_allow_html=True
    )

if st.session_state.current_page == "chat":
    # Main Workspace Layout
    col1, col2 = st.columns([7, 3])
    
    with col1:
        # Reset Confirmation and Chat Input Box placed at the Top of the feed
        if not api_key:
            st.error("🔑 **Google Gemini API Key Missing**  \nPlease copy `.env.example` to `.env` in the project root and add your `GOOGLE_API_KEY=...` to start.")
        else:
            # Warning Confirmation when clicking reset
            if st.session_state.confirm_reset:
                st.warning("⚠️ **Are you sure you want to reset this session?** All current chat history and validated steps will be lost.")
                c1, c2 = st.columns(2)
                if c1.button("Confirm Reset and Clear", type="primary", use_container_width=True):
                    st.session_state.messages = [{
                        "role": "assistant",
                        "content": "Welcome to the Root Cause AI Assistant. To begin a rigorous Sentinel Event review or clinical process investigation, please describe the patient safety event or operational failure.<br><br><i>Example: 'A clinician pulled and administered the wrong medication (Vecuronium instead of Versed) from the Pyxis cabinet under an override.'</i>",
                        "why_num": 0,
                        "is_critique": False
                    }]
                    st.session_state.validated_answers = []
                    st.session_state.initial_problem = ""
                    st.session_state.session_concluded = False
                    st.session_state.session_started = False
                    st.session_state.charter_generated = False
                    st.session_state.why_count = 0
                    st.session_state.charter_data = None
                    st.session_state.refinement_messages = []
                    st.session_state.confirm_reset = False
                    st.session_state.current_page = "chat"
                    st.rerun()
                if c2.button("Cancel Reset", use_container_width=True):
                    st.session_state.confirm_reset = False
                    st.rerun()
            
            # Show Redirection Banner if session concluded
            if st.session_state.session_concluded:
                st.markdown(
                    clean_html("""
                    <div class="concluded-banner">
                        <div class="concluded-banner-title">🎉 Root Cause Analysis Concluded!</div>
                        <div class="concluded-banner-subtitle">You have successfully validated all process steps. Proceed to the Summary page to view the visual chain and generate the A3 Project Charter.</div>
                    </div>
                    """),
                    unsafe_allow_html=True
                )
                if st.button("➡️ Proceed to Session Summary & Action Plan", type="primary", use_container_width=True):
                    st.session_state.current_page = "summary"
                    st.rerun()
                st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            
            # Grid layout to place Reset button next to the input form
            input_disabled = st.session_state.charter_generated or st.session_state.session_concluded
            placeholder_text = "RCA session completed. Proceed to the Summary Page to generate the charter." if st.session_state.session_concluded else "Type your response here and press Enter or Submit..."
            
            with st.form("chat_form", clear_on_submit=True):
                user_text = st.text_input(
                    "State the issue or answer the facilitator's why question:",
                    placeholder=placeholder_text,
                    disabled=input_disabled
                )
                
                # Render form buttons side-by-side if the session is concluded
                if st.session_state.session_concluded and not st.session_state.charter_generated:
                    c_submit, c_dig, c_res = st.columns([3, 4, 3])
                    with c_submit:
                        submit_button = st.form_submit_button("Submit Response", type="primary", disabled=True, use_container_width=True)
                    with c_dig:
                        next_why_num = st.session_state.why_count + 1
                        continue_button = st.form_submit_button(f"🔍 Continue Digging (Why #{next_why_num})", type="primary", use_container_width=True)
                    with c_res:
                        reset_button = st.form_submit_button("🔄 Reset", disabled=not st.session_state.session_started, use_container_width=True)
                else:
                    c_submit_btn, c_spacer, c_res = st.columns([3, 4, 3])
                    with c_submit_btn:
                        submit_button = st.form_submit_button("Submit Response", type="primary", disabled=input_disabled, use_container_width=True)
                    with c_res:
                        reset_button = st.form_submit_button("🔄 Reset", disabled=not st.session_state.session_started, use_container_width=True)
                    continue_button = False
            
            # Handle user submit, continue digging, or reset
            if reset_button:
                st.session_state.confirm_reset = True
                st.rerun()
            elif submit_button and user_text:
                user_input = user_text.strip()
                st.session_state.messages.append({"role": "user", "content": user_input})
                st.session_state.session_started = True
                
                with st.spinner("Analyzing response & formatting system-level critique..."):
                    try:
                        res = get_facilitator_response(
                            st.session_state.messages, 
                            st.session_state.why_count, 
                            api_key
                        )
                        
                        if res.is_critique:
                            reply = res.critique_explanation
                            is_critique = True
                            why_num = st.session_state.why_count + 1 if st.session_state.initial_problem else 0
                        elif res.is_vague:
                            reply = res.clarification_prompt
                            is_critique = False
                            why_num = st.session_state.why_count + 1 if st.session_state.initial_problem else 0
                        else:
                            is_critique = False
                            if not st.session_state.initial_problem:
                                st.session_state.initial_problem = user_input
                                why_num = 1
                                reply = res.next_why_question
                            else:
                                st.session_state.why_count += 1
                                summary = res.why_summary.strip() if getattr(res, "why_summary", None) else ""
                                if not summary:
                                    summary = user_input
                                st.session_state.validated_answers.append(summary)
                                
                                if getattr(res, "is_concluded", False) or st.session_state.why_count >= 5:
                                    st.session_state.session_concluded = True
                                    why_num = 0
                                else:
                                    why_num = st.session_state.why_count + 1
                                reply = res.next_why_question
                    except Exception as e:
                        reply = f"Error communicating with Gemini: {str(e)}"
                        is_critique = False
                        why_num = st.session_state.why_count + 1 if st.session_state.initial_problem else 0

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply,
                    "why_num": why_num,
                    "is_critique": is_critique
                })
                st.rerun()
                
            elif continue_button:
                st.session_state.session_concluded = False
                next_why_num = st.session_state.why_count + 1
                
                with st.spinner("Formulating next Why question..."):
                    try:
                        clean_history = st.session_state.messages[:-1]
                        res = get_facilitator_response(
                            clean_history,
                            st.session_state.why_count,
                            api_key,
                            force_continue=True
                        )
                        reply = res.next_why_question
                        is_critique = res.is_critique
                    except Exception as e:
                        reply = f"Error formulating next question: {str(e)}"
                        is_critique = False
                
                st.session_state.messages[-1] = {
                    "role": "assistant",
                    "content": reply,
                    "why_num": next_why_num,
                    "is_critique": is_critique
                }
                st.rerun()

        # Find the index of the most recent assistant message
        latest_assistant_idx = -1
        for idx in range(len(st.session_state.messages) - 1, -1, -1):
            if st.session_state.messages[idx]["role"] == "assistant":
                latest_assistant_idx = idx
                break

        # Display Conversations in Descending Order (newest at the top)
        st.markdown("### 💬 Conversation Feed")
        
        feed_html = '<div class="chat-container">'
        for idx, msg in enumerate(reversed(st.session_state.messages)):
            orig_idx = len(st.session_state.messages) - 1 - idx
            role = msg["role"]
            content = msg["content"]
            
            if role == "user":
                feed_html += f"""
                <div class="chat-card user">
                    <div class="role-badge">👤 Team Member</div>
                    <div class="message-content">{content}</div>
                </div>
                """
            else:
                is_latest = (orig_idx == latest_assistant_idx)
                card_class = "chat-card assistant latest" if is_latest else "chat-card assistant"
                
                is_critique = msg.get("is_critique", False)
                critique_html = ""
                if is_critique:
                    critique_html = """
                    <div class="critique-box">
                        <div class="critique-title">⚠️ Operational Excellence Guardrail</div>
                        This explanation attributes the issue to individual behavior (human error). Root Cause Analysis requires us to look past human error to process design. Why did the system or workflow allow this mistake to occur, or fail to prevent/detect it?
                    </div>
                    """
                
                why_badge_html = f'<span class="phase-badge">Why #{msg.get("why_num", 1)}</span>' if msg.get("why_num", 0) > 0 else ""
                active_indicator = '<span style="display:inline-block; width:8px; height:8px; background-color:#990000; border-radius:50%; margin-left:8px; animation: pulse 1.5s infinite;"></span>' if (is_latest and not st.session_state.session_concluded) else ""
                
                feed_html += f"""
                <div class="{card_class}">
                    <div class="role-badge">⚙️ Operational Excellence AI {why_badge_html} {active_indicator}</div>
                    <div class="message-content">{content}</div>
                    {critique_html}
                </div>
                """
        feed_html += '</div>'
        st.markdown(clean_html(feed_html), unsafe_allow_html=True)

    with col2:
        st.markdown("### 📋 Action Panel")
        
        if st.session_state.session_concluded:
            st.info("💡 Session concluded! Click the button at the top of the chat to view the final summary and generate the A3 Project Charter.")
        else:
            st.info("💡 Complete the 5 Whys session to unlock the summary and Project Charter generation.")

else:
    # Dedicated Summary & Action Plan Page
    if not api_key:
        st.error("🔑 **Google Gemini API Key Missing**  \nPlease copy `.env.example` to `.env` in the project root and add your `GOOGLE_API_KEY=...` to start.")
    else:
        # Warning Confirmation when clicking reset from summary page
        if st.session_state.confirm_reset:
            st.warning("⚠️ **Are you sure you want to reset this session?** All current chat history and validated steps will be lost.")
            rc1, rc2 = st.columns(2)
            if rc1.button("Confirm Reset and Clear", type="primary", use_container_width=True, key="summary_confirm_reset"):
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": "Welcome to the Root Cause AI Assistant. To begin a rigorous Sentinel Event review or clinical process investigation, please describe the patient safety event or operational failure.<br><br><i>Example: 'A clinician pulled and administered the wrong medication (Vecuronium instead of Versed) from the Pyxis cabinet under an override.'</i>",
                    "why_num": 0,
                    "is_critique": False
                }]
                st.session_state.validated_answers = []
                st.session_state.initial_problem = ""
                st.session_state.session_concluded = False
                st.session_state.session_started = False
                st.session_state.charter_generated = False
                st.session_state.why_count = 0
                st.session_state.charter_data = None
                st.session_state.refinement_messages = []
                st.session_state.confirm_reset = False
                st.session_state.current_page = "chat"
                st.rerun()
            if rc2.button("Cancel Reset", use_container_width=True, key="summary_cancel_reset"):
                st.session_state.confirm_reset = False
                st.rerun()

        # Navigation toolbar
        c_back, c_spacer, c_reset = st.columns([3, 6, 3])
        with c_back:
            if st.button("⬅️ Back to Conversation", type="primary", use_container_width=True, key="back_to_chat"):
                st.session_state.current_page = "chat"
                st.rerun()
        with c_reset:
            if st.button("🔄 Reset Investigation", use_container_width=True, key="reset_from_summary"):
                st.session_state.confirm_reset = True
                st.rerun()

        st.markdown("<h2 style='text-align: center; color: #990000; margin-top: 1.5rem;'>🔍 Validated 5 Whys Root Cause Chain</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; opacity: 0.8; margin-bottom: 2rem;'>Visual mapping of the safety event to its systemic root cause</p>", unsafe_allow_html=True)

        # Render visual timeline
        timeline_html = '<div class="timeline">'
        if st.session_state.initial_problem:
            timeline_html += clean_html(f"""
            <div class="timeline-item">
                <div class="timeline-badge">START</div>
                <div class="timeline-panel">
                    <div class="timeline-panel-title">Initial Event / Problem Statement</div>
                    <div class="timeline-panel-content">{st.session_state.initial_problem}</div>
                </div>
            </div>
            """)
        for i, ans in enumerate(st.session_state.validated_answers):
            timeline_html += clean_html(f"""
            <div class="timeline-item">
                <div class="timeline-badge">#{i+1}</div>
                <div class="timeline-panel">
                    <div class="timeline-panel-title">Why #{i+1}</div>
                    <div class="timeline-panel-content">{ans}</div>
                </div>
            </div>
            """)
        timeline_html += '</div>'
        st.markdown(timeline_html, unsafe_allow_html=True)

        st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)

        # Action panel to generate Project Charter
        if not st.session_state.charter_generated:
            st.markdown("<h3 style='text-align: center; color: #990000;'>📋 Ready to generate the Project Charter?</h3>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; opacity: 0.8; margin-bottom: 1.5rem;'>The AI will analyze the validated root cause path and draft a full A3 charter blueprint.</p>", unsafe_allow_html=True)
            
            cb1, cb2, cb3 = st.columns([3, 6, 3])
            with cb2:
                if st.button("📝 Generate A3 Project Charter Blueprint", type="primary", use_container_width=True, key="generate_charter_summary"):
                    st.session_state.charter_generated = True
                    st.toast("Compiling A3 Project Charter Blueprint...", icon="📝")
                    with st.spinner("Compiling A3 Project Charter..."):
                        try:
                            charter = generate_a3_charter(st.session_state.messages, api_key)
                            st.session_state.charter_data = charter
                        except Exception as e:
                            st.error(f"Error compiling charter: {str(e)}")
                    st.rerun()
        
        # Display A3 Project Charter in a 2x2 Grid
        if st.session_state.charter_generated and st.session_state.charter_data:
            charter = st.session_state.charter_data
            
            st.markdown("---")
            st.markdown("<h2 style='text-align: center; color: #990000;'>📋 A3 Project Charter Blueprint</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; opacity: 0.8; margin-bottom: 2rem;'>Formal Lean Action Plan designed to address systemic root causes</p>", unsafe_allow_html=True)
            
            countermeasures_html = "".join([f"<li>{item}</li>" for item in charter.countermeasures])
            metrics_html = "".join([f"<li>{item}</li>" for item in charter.success_metrics])
            
            grid_html = f"""
            <div class="a3-grid-container">
                <div class="a3-card">
                    <div class="a3-card-title">📋 1. Problem Statement</div>
                    <div class="a3-card-body">{charter.problem_statement}</div>
                </div>
                <div class="a3-card">
                    <div class="a3-card-title">🔍 2. Root Cause Analysis Summary</div>
                    <div class="a3-card-body">{charter.rca_summary}</div>
                </div>
                <div class="a3-card">
                    <div class="a3-card-title">🛠️ 3. Proposed Countermeasures</div>
                    <div class="a3-card-body">
                        <ul>{countermeasures_html}</ul>
                    </div>
                </div>
                <div class="a3-card">
                    <div class="a3-card-title">📊 4. Key Success Metrics</div>
                    <div class="a3-card-body">
                        <ul>{metrics_html}</ul>
                    </div>
                </div>
            </div>
            """
            st.markdown(clean_html(grid_html), unsafe_allow_html=True)
            
            # A3 Charter Refinement Copilot Workspace
            st.markdown(clean_html("""
            <div class="refinement-workspace">
                <hr>
                <h3 style='color: #990000; margin-bottom: 0.5rem;'>💬 A3 Charter Refinement Copilot</h3>
                <p style='opacity: 0.8; font-size: 0.95rem; margin-bottom: 1.5rem;'>You can have a conversation with the Copilot to discuss metrics, explore countermeasures, or make direct adjustments. Ask a question (e.g. <i>'What should my target wait times be?'</i>) or request a direct change (e.g. <i>'Change target wait time in Key Success Metrics to less than 8 minutes'</i>) and click Apply.</p>
            </div>
            """), unsafe_allow_html=True)
            
            st.markdown('<div class="refinement-form-wrapper">', unsafe_allow_html=True)
            with st.form("refinement_form", clear_on_submit=True):
                refine_input = st.text_input("Discuss ideas or describe adjustments with the Copilot:", placeholder="Ask a question or request a change here...")
                rc_btn_col, rc_spacer = st.columns([4, 8])
                with rc_btn_col:
                    refine_submit = st.form_submit_button("✏️ Send to Copilot & Update A3 Charter", type="primary", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if refine_submit and refine_input:
                user_feedback = refine_input.strip()
                st.session_state.refinement_messages.append({"role": "user", "content": user_feedback})
                
                with st.spinner("Refining A3 Project Charter..."):
                    try:
                        refinement_res = refine_a3_charter(
                            st.session_state.messages,
                            st.session_state.charter_data,
                            st.session_state.refinement_messages,
                            api_key
                        )
                        st.session_state.charter_data = refinement_res.updated_charter
                        st.session_state.refinement_messages.append({
                            "role": "assistant",
                            "content": refinement_res.explanation
                        })
                    except Exception as e:
                        st.error(f"Error refining charter: {str(e)}")
                st.rerun()
                
            if st.session_state.refinement_messages:
                st.markdown(clean_html("""
                <div class="refinement-log-header">
                    <div style='height: 1.5rem;'></div>
                    <p style='font-weight: 600; font-size: 0.95rem; margin-bottom: 0.5rem;'>Adjustment History Log:</p>
                </div>
                """), unsafe_allow_html=True)
                
                refine_feed_html = '<div class="refinement-container">'
                for r_msg in reversed(st.session_state.refinement_messages):
                    r_role = r_msg["role"]
                    r_content = r_msg["content"]
                    
                    if r_role == "user":
                        refine_feed_html += f"""
                        <div class="refinement-card user">
                            <strong>👤 Adjustment Request:</strong> {r_content}
                        </div>
                        """
                    else:
                        refine_feed_html += f"""
                        <div class="refinement-card assistant">
                            <strong>⚙️ Copilot Status:</strong> {r_content}
                        </div>
                        """
                refine_feed_html += '</div>'
                st.markdown(clean_html(refine_feed_html), unsafe_allow_html=True)
                
            st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
            st.info("ℹ️ You can print this page (Ctrl+P) or copy the text above to export this draft to your organization's document management systems.")

