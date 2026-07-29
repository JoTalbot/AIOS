from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class Template(Base):
    __tablename__ = "templates"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    intent = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    variables = relationship("TemplateVariable", back_populates="template", cascade="all, delete-orphan")


class TemplateVariable(Base):
    __tablename__ = "template_variables"
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String, ForeignKey("templates.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    required = Column(Boolean, default=True)
    default = Column(JSON, nullable=True)
    description = Column(String, nullable=True)
    template = relationship("Template", back_populates="variables")
