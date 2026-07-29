from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func

from .base import Base


class DeadLetterMessage(Base):
    __tablename__ = "dead_letter_messages"
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, nullable=False)
    payload = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    last_retry_at = Column(DateTime, nullable=True)
