from sqlalchemy import JSON, Column, DateTime, Integer, String, func

from .base import Base


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_type = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=True, index=True)
    intent = Column(String, nullable=True)
    value = Column(Integer, default=1)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
