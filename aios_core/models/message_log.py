from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text

from .base import Base


class MessageLog(Base):
    __tablename__ = "message_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False)
    sender_id = Column(String, nullable=True)
    recipient_id = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    intent = Column(String, nullable=True, index=True)
    language = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    draft_id = Column(String, nullable=True)
    template_used = Column(String, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processing_time = Column(Float, nullable=True)
