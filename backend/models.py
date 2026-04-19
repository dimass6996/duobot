from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class Dialog(Base):
    __tablename__ = "dialogs"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    dialog_code = Column(String, index=True)
    sender = Column(String)
    text = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
