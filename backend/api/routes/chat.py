from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import time
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import List

from api.schemas.chat import (
    ChatMessage,
    ChatResponse,
    ConversationHistory,
    ShareRequest,
    ShareResponse
)
from api.services.chat_service import ChatService
from api.services.clip_service import ClipService
from api.services.conversation_service import ConversationService
from api.dependencies.database import get_db
from api.dependencies.redis import get_redis

import logging

router = APIRouter()

# Add new schema for chat message with history
class ChatMessageWithHistory(ChatMessage):
    conversation_history: Optional[List[dict]] = None

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    message: ChatMessageWithHistory,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Handle chat message and return response with relevant clip"""
    try:
        # Initialize services
        chat_service = ChatService(db, redis)
        
        # Get response from chat service
        response = await chat_service.get_response(
            message=message.content,
            context={
                'conversation_history': message.conversation_history if message.conversation_history else []
            }
        )
        
        return response

    except Exception as e:
        # Log the full error for debugging
        logging.error(f"Error in chat_message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat message: {str(e)}"
        )

@router.get("/history", response_model=ConversationHistory)
async def get_chat_history(
    request: Request,
    limit: Optional[int] = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for current session"""
    try:
        session_id = request.state.session_id
        conversation_service = ConversationService(db)
        
        history = await conversation_service.get_history(
            session_id=session_id,
            limit=limit
        )
        
        return history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving chat history: {str(e)}"
        )

@router.post("/share", response_model=ShareResponse)
async def share_conversation(
    share_request: ShareRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a shareable link for a conversation"""
    try:
        conversation_service = ConversationService(db)
        
        # Create a new conversation with the provided messages
        conversation = await conversation_service.create_conversation_from_messages(
            messages=share_request.messages,
            session_id=share_request.session_id
        )
        
        # Create share link that expires in N days
        expires_at = datetime.utcnow() + timedelta(days=share_request.expire_days)
        share_url = await conversation_service.create_share_link(
            conversation.id,
            share_request.session_id,
            expires_at
        )
        
        return ShareResponse(
            share_url=share_url,
            expires_at=expires_at
        )
        
    except Exception as e:
        logging.error(f"Error sharing conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error sharing conversation: {str(e)}"
        )

@router.get("/share/{share_id}", response_model=ConversationHistory)
async def get_shared_conversation(
    share_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a shared conversation"""
    try:
        logging.info(f"Fetching shared conversation with ID: {share_id}")
        conversation_service = ConversationService(db)
        conversation = await conversation_service.get_shared_conversation(share_id)
        
        if not conversation:
            logging.warning(f"Shared conversation not found or expired: {share_id}")
            raise HTTPException(
                status_code=404,
                detail="Shared conversation not found or expired"
            )
        
        logging.info(f"Successfully retrieved shared conversation: {share_id}")    
        return conversation

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error retrieving shared conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving shared conversation: {str(e)}"
        ) 