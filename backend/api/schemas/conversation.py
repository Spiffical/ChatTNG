from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ClipMetadata(BaseModel):
    clip_path: str
    start_time: float
    end_time: float
    character: Optional[str] = None
    episode: Optional[str] = None
    season: Optional[int] = None
    confidence: Optional[float] = None

class MessageBase(BaseModel):
    """Base message schema"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    clip_url: Optional[str] = None
    subtitle_url: Optional[str] = None
    clip_metadata: Optional[ClipMetadata] = None

class MessageCreate(MessageBase):
    """Schema for creating a message"""
    conversation_history: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Previous messages in the conversation for context"
    )

class Message(MessageBase):
    """Schema for message response"""
    id: int
    conversation_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: Optional[str] = None

class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    session_id: str

class ConversationUpdate(ConversationBase):
    """Schema for updating a conversation"""
    is_shared: Optional[bool] = None

class Conversation(ConversationBase):
    """Schema for conversation response"""
    id: str
    created_at: datetime
    updated_at: datetime
    session_id: str
    is_shared: bool
    share_url: Optional[str] = None
    messages: List[Message] = []

    class Config:
        from_attributes = True

class ConversationSummary(BaseModel):
    """Schema for conversation summary"""
    id: str
    title: Optional[str]
    created_at: datetime
    message_count: int
    last_message: Optional[str]

    class Config:
        from_attributes = True

class ShareResponse(BaseModel):
    """Schema for share response"""
    share_url: str = Field(..., description="Shareable URL")

class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    messages: List[Message] = Field(default_factory=list, description="Conversation messages")

    class Config:
        from_attributes = True

class ConversationShare(BaseModel):
    """Schema for conversation share"""
    id: str = Field(..., description="Share ID")
    conversation_id: str = Field(..., description="Conversation ID")
    created_at: int = Field(..., description="Unix timestamp of creation")
    expires_at: int = Field(..., description="Unix timestamp of expiration")

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    """Schema for chat message"""
    content: str = Field(..., description="Message content")
    role: str = Field(default="user", description="Message role (user/assistant)")

class ChatResponse(BaseModel):
    """Schema for chat response"""
    text: str = Field(..., description="Response text")
    clip_url: str = Field(..., description="URL to video clip")
    subtitle_url: str = Field(..., description="URL to subtitle file")
    clip_metadata: Dict[str, Any] = Field(..., description="Clip metadata")
    conversation_id: Optional[str] = Field(None, description="Conversation ID") 