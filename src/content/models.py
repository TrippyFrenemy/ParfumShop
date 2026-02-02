from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from src.database import Base


class SiteContent(Base):
    __tablename__ = "site_content"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    page = Column(String(50), nullable=False, index=True)
    label = Column(String(255), nullable=True)
    content_type = Column(String(20), default="short")  # short | text | html
    published_value = Column(Text, nullable=True)
    draft_value = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=True, server_default="true")
    sort_order = Column(Integer, default=0, server_default="0")
    has_unpublished_changes = Column(Boolean, default=False, server_default="false")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
