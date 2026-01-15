from datetime import date, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from db import SessionLocal, Subscription, init_db
from notify import send_email

load_dotenv()

def check_and_send():
    db = SessionLocal()
    try:
        today = date.today()
        target_date = today + timedelta(days=1)  # remind one day before

        subs = (
            db.query(Subscription)
            .filter(Subscription.email_enabled == True)
            .filter(Subscription.trial_end_date == target_date)
            .all()
        )

        sent = 0
        for s in subs:
            # prevent duplicates if worker runs multiple times in a day
            if s.last_reminded_date == today:
                continue

            subject = f"GingerBOT Reminder: {s.service_name} trial ends tomorrow"
            html = f"""
            <p>Hi,</p>
            <p>Your <b>{s.service_name}</b> free trial ends on <b>{s.trial_end_date}</b>.</p>
            <p>If you don’t want to be charged, cancel before it ends.</p>
            <p>— GingerBOT</p>
            """

            send_email(s.user_email, subject, html)
            s.last_reminded_date = today
            sent += 1

        db.commit()
        print(f"[worker] Sent {sent} reminder(s). Checked {len(subs)} subscription(s).")

    finally:
        db.close()

if __name__ == "__main__":
    init_db()

    sched = BlockingScheduler(timezone="America/New_York")
    # Every day at 9:00 AM New York time
    sched.add_job(check_and_send, "cron", hour=9, minute=0)

    print("[worker] Scheduled daily check at 09:00 America/New_York")

    # IMPORTANT: keep this commented so it does NOT send immediately
    # check_and_send()

    sched.start()

