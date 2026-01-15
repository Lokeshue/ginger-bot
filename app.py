import os
import math
import json
import re
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from openai import OpenAI

from db import init_db, SessionLocal, Subscription

# ----------------------------
# Setup
# ----------------------------
load_dotenv()
init_db()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OPENAI_API_KEY. Add it to your .env file.")
    st.stop()

client = OpenAI(api_key=api_key)

st.set_page_config(page_title="GingerBOT", page_icon="🤖")
st.title("GingerBOT")

# ----------------------------
# Subscription Reminder UI
# ----------------------------
st.header("⏰ Subscription Reminders (Email)")

with st.form("add_subscription_form", clear_on_submit=True):
    service_name = st.text_input("Service name (e.g., Netflix, Adobe)", "")
    trial_end_date = st.date_input("Trial end date", value=date.today() + timedelta(days=1))
    notify_email = st.text_input("Email to notify", os.getenv("SMTP_USER", ""))

    submitted = st.form_submit_button("Add reminder")
    if submitted:
        if not service_name.strip():
            st.error("Please enter a Service name.")
        elif not notify_email.strip():
            st.error("Please enter an Email to notify.")
        else:
            db = SessionLocal()
            db.add(
                Subscription(
                    user_email=notify_email.strip(),
                    service_name=service_name.strip(),
                    trial_end_date=trial_end_date,
                    email_enabled=True,
                )
            )
            db.commit()
            db.close()
            st.success(f"Added reminder for {service_name.strip()} ending on {trial_end_date} ✅")
            st.rerun()

# List existing subscriptions
db = SessionLocal()
subs = db.query(Subscription).order_by(Subscription.trial_end_date.asc()).all()
db.close()

st.subheader("📋 Saved reminders")
if not subs:
    st.info("No reminders yet. Add one above.")
else:
    for s in subs:
        c1, c2, c3, c4 = st.columns([3, 2, 3, 1])
        c1.write(s.service_name)
        c2.write(str(s.trial_end_date))
        c3.write(s.user_email)
        if c4.button("🗑️", key=f"del_{s.id}"):
            db = SessionLocal()
            db.query(Subscription).filter(Subscription.id == s.id).delete()
            db.commit()
            db.close()
            st.rerun()

st.divider()

# ----------------------------
# Tools
# ----------------------------
def tool_web_search(query: str) -> str:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            title = r.get("title", "").strip()
            href = r.get("href", "").strip()
            body = r.get("body", "").strip()
            results.append(f"- {title}\n  {href}\n  {body}")
    return "\n".join(results) if results else "No results found."

def tool_calculator(expression: str) -> str:
    """
    Safer-ish calculator:
    - disallows suspicious characters
    - eval with no builtins, only math module
    """
    expr = (expression or "").strip()
    if not expr:
        return "Calculator error: empty expression"

    # Allow only digits, operators, parentheses, whitespace, decimal, commas, and 'math.' names.
    # This is a simple guard; for maximum safety, implement AST-based evaluation.
    if not re.fullmatch(r"[0-9\.\+\-\*\/\%\(\)\s,matha-zA-Z_]+", expr):
        return "Calculator error: invalid characters"

    allowed_globals = {"__builtins__": {}}
    safe_locals = {"math": math}
    try:
        value = eval(expr, allowed_globals, safe_locals)
        return str(value)
    except Exception as e:
        return f"Calculator error: {e}"

def tool_save_note(note: str) -> str:
    st.session_state.notes.append(note)
    return "Saved."

def tool_list_notes(_: str = "") -> str:
    if not st.session_state.notes:
        return "No notes saved yet."
    return "\n".join([f"{i+1}. {n}" for i, n in enumerate(st.session_state.notes)])

TOOLS = {
    "web_search": tool_web_search,
    "calculator": tool_calculator,
    "save_note": tool_save_note,
    "list_notes": tool_list_notes,
}

tool_schemas = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date information.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a math expression.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Save a note for later.",
            "parameters": {
                "type": "object",
                "properties": {"note": {"type": "string"}},
                "required": ["note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "List saved notes.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# ----------------------------
# Chat UI + Agent Loop
# ----------------------------
st.header("💬 Chat")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are GingerBOT, an agentic assistant. "
                "If a tool would help (web_search, calculator, save_note, list_notes), call it. "
                "Keep answers clear and concise."
            ),
        }
    ]

if "notes" not in st.session_state:
    st.session_state.notes = []

# Render chat history
for m in st.session_state.messages:
    if m["role"] in ("user", "assistant"):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

user_text = st.chat_input("Ask something…")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # First call: allow tool use
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=st.session_state.messages,
        tools=tool_schemas,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    # If no tool calls, respond directly
    if not getattr(msg, "tool_calls", None):
        st.session_state.messages.append({"role": "assistant", "content": msg.content or ""})
        with st.chat_message("assistant"):
            st.markdown(msg.content or "")
    else:
        # Execute each tool call
        for tc in msg.tool_calls:
            fn_name = tc.function.name

            try:
                args = json.loads(tc.function.arguments or "{}")  # ✅ safe JSON parse
            except json.JSONDecodeError:
                args = {}

            if fn_name not in TOOLS:
                out = f"Unknown tool: {fn_name}"
            else:
                try:
                    if fn_name == "web_search":
                        out = TOOLS[fn_name](args.get("query", ""))
                    elif fn_name == "calculator":
                        out = TOOLS[fn_name](args.get("expression", ""))
                    elif fn_name == "save_note":
                        out = TOOLS[fn_name](args.get("note", ""))
                    elif fn_name == "list_notes":
                        out = TOOLS[fn_name]("")
                    else:
                        out = "Tool call not handled."
                except Exception as e:
                    out = f"Tool error ({fn_name}): {e}"

            # Append tool output
            st.session_state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": out,
                }
            )

        # Second call: final answer using tool outputs
        final = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=st.session_state.messages,
        )

        final_text = final.choices[0].message.content or ""
        st.session_state.messages.append({"role": "assistant", "content": final_text})
        with st.chat_message("assistant"):
            st.markdown(final_text)
