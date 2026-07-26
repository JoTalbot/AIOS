from sqlalchemy import Column, String, Boolean, DateTime, Integer
from datetime import datetime
from aios_core.models.base import Base

class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    owner_id = Column(String, nullable=False)
    subscription_tier = Column(String, default="free") # free, pro, enterprise
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, nullable=False)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    status = Column(String, default="incomplete") # active, past_due, canceled
    current_period_end = Column(DateTime, nullable=True)
