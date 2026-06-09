import os
from llm import get_facilitator_response

# Load env
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip() and not line.startswith("#") and "=" in line:
                parts = line.strip().split("=", 1)
                if len(parts) == 2:
                    key, val = parts
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("API Key not found!")
    exit(1)

messages = [
    {"role": "assistant", "content": "Welcome... describe event"},
    {"role": "user", "content": "Patient wait times are 15 minutes when checking in but should be closer to 5 minutes."},
    {"role": "assistant", "content": "Why are patient wait times averaging 15 minutes instead of 5 minutes?", "why_num": 1},
    {"role": "user", "content": "Staff are answering phones while registering patients."},
    {"role": "assistant", "content": "Why are front desk staff assigned to handle both incoming phone calls and in-person patient registration simultaneously?", "why_num": 2},
    {"role": "user", "content": "Policy decision of something that has always been there. It has not been looked at."}
]

res = get_facilitator_response(messages, 1, api_key)
print("Response fields:")
print(f"is_critique: {res.is_critique}")
print(f"is_vague: {res.is_vague}")
print(f"why_summary: {repr(res.why_summary)}")
print(f"next_why_question: {repr(res.next_why_question)}")
