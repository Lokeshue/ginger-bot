import os
import math
import streamlit as st
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Agentic AI Chatbot", page_icon="🤖")
st.title("GingerBOT")

def tool_web_search(query: str) -> str:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(f"- {r.get('title')}\n  {r.get('href')}\n  {r.get('body')}")
    return "\n".join(results) if results else "No results found."

def tool_calculator(expression: str) -> str:
    allowed = {"__builtins__": {}}
    safe_locals = {"math": math}
    try:
        value = eval(expression, allowed, safe_locals)
        return str(value)
    except Exception as e:
        return f"Calculator error: {e}"

def tool_save_note(note: str) -> str:
    st.session_state.notes.append(note)
    return "Saved."

def tool_list_notes() -> str:
    if not st.session_state.notes:
        return "No notes saved yet."
    return "\n".join([f"{i+1}. {n}" for i, n in enumerate(st.session_state.notes)])

TOOLS = {
    "web_search": tool_web_search,
    "calculator": tool_calculator,
    "save_note": tool_save_note,
    "list_notes": lambda _="": tool_list_notes(),
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
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are an agentic assistant. "
                "If a tool would help (web_search, calculator, save_note, list_notes), call it."
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

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=st.session_state.messages,
        tools=tool_schemas,
        tool_choice="auto",
    )

    msg = response.choices[0].message

    if not getattr(msg, "tool_calls", None):
        st.session_state.messages.append({"role": "assistant", "content": msg.content})
        with st.chat_message("assistant"):
            st.markdown(msg.content)
    else:
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            args = eval(tc.function.arguments)

            if fn_name == "web_search":
                out = TOOLS[fn_name](args["query"])
            elif fn_name == "calculator":
                out = TOOLS[fn_name](args["expression"])
            elif fn_name == "save_note":
                out = TOOLS[fn_name](args["note"])
            elif fn_name == "list_notes":
                out = TOOLS[fn_name]("")
            else:
                out = f"Unknown tool: {fn_name}"

            st.session_state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": out,
                }
            )

        final = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=st.session_state.messages,
        )

        final_text = final.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": final_text})
        with st.chat_message("assistant"):
            st.markdown(final_text)
