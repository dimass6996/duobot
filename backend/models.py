from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
import datetime

# Базовый класс для моделей
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    
    # Структура согласно ТЗ 
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(String)
    message_text = Column(String)
    file_path = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    is_read = Column(Boolean, default=False)
