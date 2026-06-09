from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class FacilitatorResponse(BaseModel):
    is_critique: bool = Field(
        description="True ONLY if the user attributes the failure to individual human error, carelessness, distraction (e.g. phone), or blame. Set to False for process-oriented answers."
    )
    critique_explanation: str = Field(
        description="Required if is_critique is True. A polite explanation of why individual blame is an RCA trap, guiding them to process design elements."
    )
    is_vague: bool = Field(
        description="True if the response is too generic, short, or vague (e.g., 'it broke', 'I don't know', 'system error') to identify a process step."
    )
    clarification_prompt: str = Field(
        description="Required if is_vague is True. A request for specific details, timeline, or system sequence to clarify the generic response."
    )
    next_why_question: str = Field(
        description="The next specific 'Why' question to advance the root-cause analysis. If the session concludes (is_concluded is True), this field must instead contain a final conclusion statement summarizing the session and guiding the user to click 'Generate Project Charter / A3 Draft'."
    )
    why_level: int = Field(
        description="The current validated Why level (1 to 5). Keep it the same as the previous level if is_critique or is_vague is True. Otherwise, increment by 1."
    )
    why_summary: str = Field(
        description="Required if is_critique and is_vague are False. A concise, one-sentence process-focused summary of the validated cause confirmed in the user's latest response. Leave empty if is_critique or is_vague is True."
    )
    is_concluded: bool = Field(
        description="Set to True if the session should conclude. This happens when: (1) we have validated Why #5, OR (2) the user's latest response has identified a fundamental, actionable system-level root cause (e.g. policy design gap, lack of standardized automation) and asking further 'Why' questions would be circular/redundant."
    )

class A3ProjectCharter(BaseModel):
    problem_statement: str = Field(
        description="Clear, concise, data-driven description of the process or sentinel failure event."
    )
    rca_summary: str = Field(
        description="Summary of the 5 Whys logic path and the ultimate systemic root cause identified."
    )
    countermeasures: list[str] = Field(
        description="List of proposed, actionable system-level countermeasures designed to address the root cause and prevent recurrence."
    )
    success_metrics: list[str] = Field(
        description="List of operational or safety metrics to track the effectiveness of the countermeasures."
    )

SYSTEM_PROMPT = """You are the **Operational Excellence AI**, an expert process improvement facilitator specializing in Lean Six Sigma and Sentinel Event Root Cause Analysis (RCA) in healthcare.

Your task is to guide a Team Member through a rigorous "5 Whys" session. You must analyze their latest response and return a structured assessment:

### Core Instructions:
1. **Intercept Blame/Human Error**: If the Team Member attributes the event to individual behavior (e.g., "nurse was on phone", "clinician forgot", "someone made a mistake", "they bypassed it"), set `is_critique = True`. Explain why focusing on human error is an RCA trap (processes should prevent or absorb human mistakes). Prompt them for system/process factors instead (e.g., barcode configurations, double-check policies). Do NOT increment the why_level.
2. **Intercept Vague Answers**: If the response is generic or short (e.g. "I don't know", "it broke", "system failed"), set `is_vague = True`. Request clarification on the exact process step or technical detail. Do NOT increment the why_level.
3. **Progress Valid Whys**: If the response is process-oriented (e.g., "the database was down because of a backup script migration failure", "pharmacy backlog due to software transition"), set `is_critique = False` and `is_vague = False`. Ask the next logical "Why" question. Increment the why_level. Also provide `why_summary`, which MUST be a concise, professional, process-focused translation of their answer into formal operational excellence/clinical safety terminology (e.g., translating "we always did it this way" to "governed by legacy operational policies without periodic review"). It must not copy the user's raw response.
4. **Session Conclusion**: Determine if the session should conclude (`is_concluded = True`). The session is complete when:
   - The Why level reaches 5.
   - OR, the user's latest response has identified a fundamental, actionable system/process-level root cause (e.g., completely missing policy reviews, lack of software configuration guardrails, legacy workflow designs) where asking further "Why" questions would be redundant, circular, or meaningless.
   If concluding, set `is_concluded = True`, and provide a warm final conclusion summarizing the root cause in `next_why_question` instead of a new question. Otherwise, set `is_concluded = False`.
"""

def get_facilitator_response(messages: list, current_why_level: int, api_key: str, force_continue: bool = False) -> FacilitatorResponse:
    """
    Connects to the Google Gemini model via LangChain to analyze the conversation
    and extract structured feedback using the Pydantic schema.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=api_key,
        temperature=0.2,
    )
    
    structured_llm = llm.with_structured_output(FacilitatorResponse)
    
    formatted_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        else:
            content = msg["content"]
            formatted_messages.append(AIMessage(content=content))
            
    # Append dynamic system instructions to guide structured outputs and step counting
    user_msgs = [m for m in messages if m["role"] == "user"]
    if current_why_level == 0 and len(user_msgs) == 1:
        state_prompt = "Instruction: The user has just described the initial problem statement. Validate it. If valid, ask the question for Why #1. Set is_concluded to False."
    elif force_continue:
        # Force the LLM to skip conclusion and formulate the next question
        next_level = current_why_level + 1
        state_prompt = f"Instruction: The user has elected to continue the investigation beyond a previous stop. Do not conclude the session. Set is_concluded to False, and ask the next logical 'Why' question for Why #{next_level + 1}."
    else:
        next_level = current_why_level + 1
        if next_level < 5:
            state_prompt = f"Instruction: The user is answering the question for Why #{next_level}. If valid, summarize it as why_summary. If you determine that the root cause has been reached (fundamental, actionable system/process failure where further 'Why' is circular/meaningless), set is_concluded to True, summarize the final conclusion in next_why_question, and do not ask another question. Otherwise, set is_concluded to False and ask the next question for Why #{next_level + 1}."
        else:
            state_prompt = f"Instruction: The user is answering the question for Why #{next_level}. If valid, summarize it as why_summary. If they are ready to conclude (or if you determine a final root cause is reached), set is_concluded to True and summarize the conclusion in next_why_question. Otherwise, set is_concluded to False and ask the next question for Why #{next_level + 1}."
            
    formatted_messages.append(SystemMessage(content=state_prompt))
            
    response = structured_llm.invoke(formatted_messages)
    return response

def generate_a3_charter(messages: list, api_key: str) -> A3ProjectCharter:
    """
    Analyzes the complete conversation history and compiles a structured
    A3 Project Charter Blueprint.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=api_key,
        temperature=0.3,
    )
    
    structured_llm = llm.with_structured_output(A3ProjectCharter)
    
    charter_prompt = """You are an expert Operational Excellence consultant. Analyze the provided conversation history of a "5 Whys" root-cause analysis session. 
    Compile a structured A3 Project Charter Blueprint based on the discussion, focusing on process design failures rather than human blame.
    """
    
    formatted_messages = [SystemMessage(content=charter_prompt)]
    for msg in messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        else:
            formatted_messages.append(AIMessage(content=msg["content"]))
            
    response = structured_llm.invoke(formatted_messages)
    return response

class RefinementResponse(BaseModel):
    updated_charter: A3ProjectCharter = Field(
        description="The updated A3 Project Charter. If the user's message is a question, comment, or suggestion seeking advice or discussion rather than direct adjustments, keep the charter fields completely unchanged."
    )
    explanation: str = Field(
        description="Your friendly and professional verbal response to the user. Answer their questions, provide consulting guidance on standard targets (e.g. standard wait times vs operational realities), explain what changes were made, or ask clarifying questions to help them design the metrics."
    )

def refine_a3_charter(messages: list, current_charter: A3ProjectCharter, refinement_messages: list, api_key: str) -> RefinementResponse:
    """
    Refines and updates the A3 Project Charter based on user feedback and refinement dialogue.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=api_key,
        temperature=0.2,
    )
    
    structured_llm = llm.with_structured_output(RefinementResponse)
    
    system_prompt = f"""You are an expert Operational Excellence consultant specializing in Lean Six Sigma process improvement.
    Your task is to refine and update the current A3 Project Charter based on the user's adjustments and feedback.
    
    ### CURRENT A3 PROJECT CHARTER BLUEPRINT:
    - **Problem Statement**: {current_charter.problem_statement}
    - **Root Cause Analysis Summary**: {current_charter.rca_summary}
    - **Proposed Countermeasures**: {current_charter.countermeasures}
    - **Key Success Metrics**: {current_charter.success_metrics}
    
    ### REFINEMENT INSTRUCTIONS:
    1. Retain all correct and relevant process-focused findings from the current charter.
    2. Directly apply the adjustments, edits, or corrections requested by the user in the refinement session (e.g. changing target wait times, updating specific counters, adding or deleting items).
    3. Maintain a strictly systemic, process-oriented perspective. Avoid introducing individual human blame.
    4. **Handle Discussion and Questions**: If the user is asking a question, seeking advice, or starting a discussion (e.g., "What should my wait times be?" or "What countermeasures do you suggest?"), DO NOT invent arbitrary figures or make guesses. Keep all the fields of the `updated_charter` completely unchanged. Instead, use the `explanation` field to suggest ideas, provide consulting guidance on industry standard metrics (e.g. typical emergency room or clinic wait times, etc.), and invite them to decide.
    5. **Apply Updates**: If the user specifies a concrete adjustment (e.g. 'Set target wait time to less than 8 minutes'), apply those changes to the fields of `updated_charter`, and describe the modification in the `explanation` field.
    """
    
    formatted_messages = [SystemMessage(content=system_prompt)]
    
    # Ingest the refinement conversation history
    for msg in refinement_messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        else:
            formatted_messages.append(AIMessage(content=msg["content"]))
            
    response = structured_llm.invoke(formatted_messages)
    return response



