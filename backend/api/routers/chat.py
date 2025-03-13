from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, Request, BackgroundTasks, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging

from api.database import get_db
from api.services.chat_service import ChatService
from api.services.conversation_service import ConversationService
from api.schemas.conversation import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationSummary,
    Message,
    MessageCreate
)
from api.schemas.chat import (
    ChatMessage,
    ChatResponse,
    ConversationHistory,
    ShareRequest,
    ShareResponse
)
from api.websockets.chat import chat_websocket_endpoint
from api.dependencies.redis import get_redis

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

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

@router.post("/conversations", response_model=Conversation)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation"""
    logger.debug(f"Creating conversation with session_id: {conversation.session_id}")
    conversation_service = ConversationService(db)
    result = await conversation_service.create_conversation(conversation)
    logger.debug(f"Created conversation with ID: {result.id}")
    return result

@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get a conversation by ID"""
    logger.debug(f"Getting conversation {conversation_id} for session {session_id}")
    conversation_service = ConversationService(db)
    conversation = await conversation_service.get_conversation(
        conversation_id,
        session_id
    )
    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List conversations for a session"""
    logger.debug(f"Listing conversations for session {session_id}")
    conversation_service = ConversationService(db)
    conversations = await conversation_service.list_conversations(session_id, skip, limit)
    logger.debug(f"Found {len(conversations)} conversations")
    return conversations

@router.patch("/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    update_data: ConversationUpdate,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update a conversation"""
    logger.debug(f"Updating conversation {conversation_id}")
    conversation_service = ConversationService(db)
    conversation = await conversation_service.update_conversation(
        conversation_id,
        update_data,
        session_id
    )
    if not conversation:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.post("/conversations/{conversation_id}/messages", response_model=Message)
async def add_message(
    conversation_id: str,
    message: MessageCreate,
    request: Request,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Add a message to a conversation"""
    logger.debug(f"Adding message to conversation {conversation_id}")
    logger.debug(f"Message content: {message.content}")
    
    # First add the user message
    conversation_service = ConversationService(db)
    db_message = await conversation_service.add_message(
        conversation_id,
        message,
        session_id
    )
    if not db_message:
        logger.warning(f"Conversation {conversation_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    # If it's a user message, generate assistant response
    if message.role == "user":
        logger.debug("Generating assistant response")
        chat_service = ChatService(db, request.app.state.redis)
        try:
            response = await chat_service.get_response(
                message.content,
                session_id,
                context={
                    'conversation_history': message.conversation_history if message.conversation_history else []
                }
            )
            
            # Create assistant message with clip metadata
            assistant_message = MessageCreate(
                role="assistant",
                content=response.text,
                clip_url=response.clip_url,
                subtitle_url=response.subtitle_url,
                clip_metadata={
                    "clip_path": response.clip_metadata.clip_path,
                    "start_time": response.clip_metadata.start_time,
                    "end_time": response.clip_metadata.end_time,
                    "character": response.clip_metadata.character,
                    "episode": response.clip_metadata.episode,
                    "season": response.clip_metadata.season,
                    "confidence": response.clip_metadata.confidence
                }
            )
            
            logger.debug(f"Creating assistant message with subtitle URL: {response.subtitle_url}")
            db_message = await conversation_service.add_message(
                conversation_id,
                assistant_message,
                session_id
            )
            logger.debug(f"Created message with ID {db_message.id}, subtitle URL: {db_message.subtitle_url}")
            logger.debug("Assistant response added successfully")
        except Exception as e:
            logger.error(f"Error generating assistant response: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        
    return db_message

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation"""
    conversation_service = ConversationService(db)
    if not await conversation_service.delete_conversation(conversation_id, session_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "success"}

@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    session_id: Optional[str] = None
):
    """WebSocket endpoint for real-time chat updates"""
    await chat_websocket_endpoint(websocket, session_id or "anonymous", conversation_id) 