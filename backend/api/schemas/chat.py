from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ClipMetadata(BaseModel):
    """Metadata for a video clip"""
    clip_path: str
    start_time: float
    end_time: float
    character: Optional[str] = None
    episode: Optional[str] = None
    season: Optional[str] = None
    confidence: Optional[float] = None

class ChatMessage(BaseModel):
    """Chat message from user"""
    content: str = Field(..., min_length=1, max_length=1000)
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    """Response to a chat message"""
    text: str
    clip_url: str
    subtitle_url: str  # URL to the SRT subtitle file
    clip_metadata: ClipMetadata
    conversation_id: str

class MessageHistory(BaseModel):
    """Single message in conversation history"""
    message: str
    response: str
    timestamp: int
    clip_metadata: Optional[ClipMetadata] = None

class ConversationHistory(BaseModel):
    """Full conversation history"""
    conversation_id: str
    messages: List[MessageHistory]
    created_at: datetime
    updated_at: datetime

class ShareRequest(BaseModel):
    """Request to share a conversation"""
    messages: List[Dict[str, Any]] = Field(..., description="Messages to share")
    session_id: str = Field(..., description="Session ID of the user sharing the conversation")
    expire_days: int = Field(default=7, ge=1, le=30, description="Number of days until the share link expires")

class ShareResponse(BaseModel):
    """Response with share URL"""
    share_url: str
    expires_at: datetime 