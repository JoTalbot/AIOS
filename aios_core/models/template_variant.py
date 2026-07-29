from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func

from .base import Base


class TemplateVariant(Base):
    __tablename__ = "template_variants"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String, ForeignKey("templates.id"), nullable=False)
    variant_name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    impressions = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
