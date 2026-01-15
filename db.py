from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
engine = create_engine("sqlite:///gingerbot.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_email = Column(String, nullable=False)
    service_name = Column(String, nullable=False)

    # store trial end as a DATE (simpler and avoids timezone issues)
    trial_end_date = Column(Date, nullable=False)

    email_enabled = Column(Boolean, default=True)
    last_reminded_date = Column(Date, nullable=True)  # prevents duplicate sends

    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)

