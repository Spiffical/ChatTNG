from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import datetime
import uuid

from api.database import Base

class Conversation(AsyncAttrs, Base):
    """Conversation model for storing chat sessions"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    session_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=True)
    is_shared = Column(Boolean, default=False)
    share_url = Column(String, nullable=True, unique=True)
    
    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", lazy="selectin")
    shares = relationship("SharedConversation", back_populates="conversation", lazy="selectin")

class Message(AsyncAttrs, Base):
    """Message model for storing individual messages in a conversation"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(String, nullable=False)
    
    # Clip metadata for assistant messages
    clip_path = Column(String, nullable=True)
    clip_url = Column(String, nullable=True)
    subtitle_url = Column(String, nullable=True)  # URL to the subtitle file
    clip_start_time = Column(Float, nullable=True)
    clip_end_time = Column(Float, nullable=True)
    clip_character = Column(String, nullable=True)
    clip_episode = Column(String, nullable=True)
    clip_season = Column(Integer, nullable=True)
    clip_confidence = Column(Float, nullable=True)
    
    # Additional metadata
    message_metadata = Column(JSON, nullable=True)
    
    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")

class SharedConversation(AsyncAttrs, Base):
    """Model for storing shared conversation links"""
    __tablename__ = "shared_conversations"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    session_id = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    conversation = relationship("Conversation", back_populates="shares") 