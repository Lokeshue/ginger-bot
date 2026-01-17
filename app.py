import os
import math
import json
import re
from datetime import date, timedelta

import streamlit as st
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from openai import OpenAI, BadRequestError

from db import init_db, SessionLocal, Subscription

# ----------------------------
# Setup
# ----------------------------
load_dotenv()
init_db()

st.set_page_config(page_title="GingerBOT", page_icon="🤖")
st.title("GingerBOT")

def get_secret(name: str, default: str = "") -> str:
    val = os.getenv(name)
    if val:
        return val
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

api_key = get_secret("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OPENAI_API_KEY. Add it to Streamlit Secrets or your .env file.")
    st.stop()

client = OpenAI(api_key=api_key)
MODEL = get_secret("OPENAI_MODEL", "gpt-4o-mini")

# ----------------------------
# Subscription Reminder UI
# ----------------------------
st.header("Subscription Reminders (Email)")

with st.form("add_subscription_form", clear_on_submit=True):
    service_name = st.text_input("Service name (e.g., Netflix, Adobe)", "")
    trial_end_date = st.date_input("Trial end date", value=date.today() + timedelta(days=1))

    default_email = get_secret("SMTP_USER", "")
    notify_email = st.text_input("Email to notify", default_email)

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
            st.success(f"Added reminder for {service_name.strip()} ending on {trial_end_date}")
            st.rerun()

db = SessionLocal()
subs = db.query(Subscription).order_by(Subscription.trial_end_date.asc()).all()
db.close()

st.subheader("Saved reminders")
if not subs:
    st.info("No reminders yet. Add one above.")
else:
    for s in subs:
        c1, c2, c3, c4 = st.columns([3, 2, 3, 1])
        c1.write(s.service_name)
        c2.write(str(s.trial_end_date))
        c3.write(s.user_email)
        if c4.button("Delete", key=f"del_{s.id}"):
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
    query = (query or "").strip()
    if not query:
        return "No query provided."
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                title = (r.get("title") or "").strip()
                href = (r.get("href") or "").strip()
                body = (r.get("body") or "").strip()
                results.append(f"- {title}\n  {href}\n  {body}")
    except Exception as e:
        return f"Web search error: {e}"
    return "\n".join(results) if results else "No results found."

def tool_calculator(expression: str) -> str:
    expr = (expression or "").strip()
    if not expr:
        return "Calculator error: empty expression"
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
    note = (note or "").strip()
    if not note:
        return "Nothing to save."
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
st.header("Chat")

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

for m in st.session_state.messages:
    if m["role"] in ("user", "assistant"):
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

user_text = st.chat_input("Ask something…")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    # 1) First call: allow tool use
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=st.session_state.messages,
            tools=tool_schemas,
            tool_choice="auto",
        )
    except BadRequestError:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=st.session_state.messages,
            tools=tool_schemas,
            tool_choice="auto",
        )

    msg = response.choices[0].message

    # If no tool calls, respond directly
    if not getattr(msg, "tool_calls", None):
        assistant_text = msg.content or ""
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
    else:
        # ✅ FIX: Append the assistant tool_calls message BEFORE tool outputs
        assistant_tool_calls = []
        for tc in msg.tool_calls:
            assistant_tool_calls.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": assistant_tool_calls,
            }
        )

        # Execute each tool call and append tool output
        for tc in msg.tool_calls:
            fn_name = tc.function.name

            try:
                args = json.loads(tc.function.arguments or "{}")
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

            st.session_state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": out,
                }
            )

        # 2) Second call: final answer using tool outputs
        try:
            final = client.chat.completions.create(
                model=MODEL,
                messages=st.session_state.messages,
            )
        except BadRequestError:
            final = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=st.session_state.messages,
            )

        final_text = final.choices[0].message.content or ""
        st.session_state.messages.append({"role": "assistant", "content": final_text})
        with st.chat_message("assistant"):
            st.markdown(final_text)
