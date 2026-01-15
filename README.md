# GingerBOT – Agentic AI Chatbot with Subscription Reminders

GingerBOT is an agentic AI chatbot built with Python, Streamlit, and OpenAI that autonomously reasons, selects tools, and executes actions. In addition to web search, calculations, and note memory, GingerBOT includes a real-world subscription reminder system that automatically sends email alerts before free trials expire.

This project demonstrates agent orchestration, background job scheduling, database persistence, and email automation in a clean, production-style architecture.

---

## Features

### Agentic AI Chatbot
- Multi-turn conversational AI  
- Autonomous tool selection and execution  
- OpenAI-powered reasoning  

### Web Search Tool
- Real-time search using DuckDuckGo  
- Retrieves up-to-date information directly in chat  

### Calculator Tool
- Safely evaluates mathematical expressions  

### Notes Memory
- Save and list notes during the conversation  
- Session-based memory management  

### Subscription Reminder System
- Add subscriptions with trial end dates via UI  
- Automatically sends email reminders 1 day before trial ends  
- Prevents duplicate reminders  
- Persistent storage using SQLite  

### Email Automation (Gmail SMTP)
- Secure email sending using Gmail App Password  
- Background worker sends scheduled reminders daily  
- Fully automated – no manual triggers required  

---

## Tech Stack

- Python 3.12+  
- Streamlit – UI framework  
- OpenAI API – LLM reasoning and tool calling  
- APScheduler – Background job scheduler  
- SQLite + SQLAlchemy – Database  
- DuckDuckGo Search – Web search tool  
- Gmail SMTP – Email delivery  
- python-dotenv – Environment management  

---

## Project Structure

ginger-bot/
├── app.py            # Streamlit UI + Agentic chatbot + Subscription UI  
├── db.py             # SQLite models and DB initialization  
├── worker.py         # Background scheduler for email reminders  
├── notify.py         # Gmail SMTP email sender  
├── requirements.txt  # Python dependencies  
├── README.md         # Project documentation  
├── .gitignore        # Ignored files (env, venv, db, etc.)  

---

## Setup Instructions

### 1. Clone the repository
git clone https://github.com/Lokeshue/ginger-bot.git  
cd ginger-bot  

### 2. Create virtual environment
python -m venv .venv  
source .venv/bin/activate  

### 3. Install dependencies
pip install -r requirements.txt  

---

## Environment Variables

Create a .env file in the project root:

OPENAI_API_KEY=your_openai_key_here  

SMTP_HOST=smtp.gmail.com  
SMTP_PORT=587  
SMTP_USER=yourgmail@gmail.com  
SMTP_PASS=your_gmail_app_password  
FROM_NAME=GingerBOT  

Important: Use a Gmail App Password, not your regular Gmail password.

---

## Running the App

### Start the Streamlit UI
streamlit run app.py  

### Start the Background Worker (in a new terminal)
python worker.py  

The worker runs daily at 9:00 AM (America/New_York) and sends reminders automatically.

---

## Adding Subscription Reminders

You can add reminders directly from the GingerBOT UI:

1. Enter service name (e.g., Netflix, Adobe)  
2. Select trial end date  
3. Enter email address  
4. Click Add Reminder  

GingerBOT will automatically send an email one day before the trial ends.

---

## Example Use Cases

- Avoid getting charged after free trials  
- Personal finance automation  
- AI assistant with real-world actions  
- Demonstration of agentic AI architecture  
- Portfolio project for AI, Data, and ML roles  

---

## Why This Project Is Special

This is not a basic chatbot.  
GingerBOT showcases:

- Agent-based reasoning  
- Tool orchestration  
- Background job scheduling  
- Persistent storage  
- Real email workflows  
- Clean architecture  
- Production-style design  

Perfect for:
- AI Engineer  
- ML Engineer  
- Data Scientist  
- GenAI roles  
- Product-focused engineering roles  

---

## Author

Lokesh Umamaheswari Ethirajan  
Master’s in Data Science – University of New Haven  
GitHub: https://github.com/Lokeshue  

---

## License
MIT License

---

## Future Enhancements

- Multi-user authentication  
- RAG (PDF upload and document Q&A)  
- Google Calendar integration  
- Stripe subscription billing  
- WhatsApp and SMS reminders  
- Cloud deployment (Render, Fly.io)  

---

If you like this project, star the repo.