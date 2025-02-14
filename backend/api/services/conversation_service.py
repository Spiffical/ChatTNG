from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert, update, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import uuid
import time
from datetime import datetime, timedelta

from api.models.conversation import Conversation, Message, SharedConversation
from api.schemas.chat import ConversationHistory, MessageHistory, ClipMetadata
from api.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationSummary,
    MessageCreate
)

class ConversationService:
    def __init__(self, db: AsyncSession):
        """Initialize conversation service with database session"""
        self.db = db

    async def add_chat_message(
        self,
        session_id: str,
        message: str,
        response_text: str,
        clip_metadata: Dict[str, Any],
        conversation_id: Optional[str] = None
    ) -> str:
        """Add a message to conversation history"""
        # Create conversation if needed
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            stmt = insert(Conversation).values(
                id=conversation_id,
                session_id=session_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await self.db.execute(stmt)
        else:
            # Update conversation timestamp
            stmt = update(Conversation).where(
                Conversation.id == conversation_id
            ).values(
                updated_at=datetime.utcnow()
            )
            await self.db.execute(stmt)
            
        # Add message
        stmt = insert(Message).values(
            conversation_id=conversation_id,
            role="user",
            content=message,
            created_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        
        # Add response
        stmt = insert(Message).values(
            conversation_id=conversation_id,
            role="assistant",
            content=response_text,
            created_at=datetime.utcnow(),
            clip_path=clip_metadata.get("clip_path") if clip_metadata else None,
            clip_start_time=clip_metadata.get("start_time") if clip_metadata else None,
            clip_end_time=clip_metadata.get("end_time") if clip_metadata else None,
            clip_character=clip_metadata.get("character") if clip_metadata else None,
            clip_episode=clip_metadata.get("episode") if clip_metadata else None,
            clip_season=int(float(clip_metadata.get("season"))) if clip_metadata and clip_metadata.get("season") else None,
            clip_confidence=clip_metadata.get("confidence") if clip_metadata else None,
            message_metadata=clip_metadata
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        return conversation_id

    async def get_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> ConversationHistory:
        """Get conversation history for session"""
        # Get latest conversation
        stmt = select(Conversation).where(
            Conversation.session_id == session_id
        ).order_by(
            Conversation.updated_at.desc()
        ).limit(1)
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return ConversationHistory(
                conversation_id="",
                messages=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
        # Get messages
        stmt = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(
            Message.created_at.desc()
        ).limit(limit)
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        return ConversationHistory(
            conversation_id=conversation.id,
            messages=[
                MessageHistory(
                    message=msg.content if msg.role == "user" else "",
                    response=msg.content if msg.role == "assistant" else "",
                    timestamp=int(msg.created_at.timestamp()),
                    clip_metadata=ClipMetadata(
                        clip_path=msg.clip_path,
                        start_time=msg.clip_start_time,
                        end_time=msg.clip_end_time,
                        character=msg.clip_character,
                        episode=msg.clip_episode,
                        season=str(msg.clip_season) if msg.clip_season else None,
                        confidence=msg.clip_confidence
                    ) if msg.role == "assistant" and msg.clip_path else None
                )
                for msg in messages
            ],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

    async def create_share_link(
        self,
        conversation_id: str,
        session_id: str,
        expires_at: datetime
    ) -> str:
        """Create shareable link for conversation"""
        share_id = str(uuid.uuid4())
        
        stmt = insert(SharedConversation).values(
            id=share_id,
            conversation_id=conversation_id,
            session_id=session_id,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        return f"/share/{share_id}"

    async def get_shared_conversation(
        self,
        share_id: str
    ) -> Optional[ConversationHistory]:
        """Get shared conversation by ID"""
        # Get share record
        stmt = select(SharedConversation).where(
            SharedConversation.id == share_id,
            SharedConversation.expires_at > datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        share = result.scalar_one_or_none()
        
        if not share:
            return None
            
        # Get conversation
        stmt = select(Conversation).where(
            Conversation.id == share.conversation_id
        )
        result = await self.db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            return None
            
        # Get messages
        stmt = select(Message).where(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at.asc())
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        return ConversationHistory(
            conversation_id=conversation.id,
            messages=[
                MessageHistory(
                    message=msg.content if msg.role == "user" else "",
                    response=msg.content if msg.role == "assistant" else "",
                    timestamp=int(msg.created_at.timestamp()),
                    clip_metadata=ClipMetadata(
                        clip_path=msg.clip_path,
                        start_time=msg.clip_start_time,
                        end_time=msg.clip_end_time,
                        character=msg.clip_character,
                        episode=msg.clip_episode,
                        season=str(msg.clip_season) if msg.clip_season else None,
                        confidence=msg.clip_confidence
                    ) if msg.role == "assistant" and msg.clip_path else None
                )
                for msg in messages
            ],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )

    async def _get_conversation(
        self,
        session_id: str
    ) -> Optional[Conversation]:
        """Get the most recent conversation for a session"""
        stmt = select(Conversation).where(
            Conversation.session_id == session_id
        ).order_by(
            Conversation.created_at.desc()
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_conversation_by_id(
        self,
        conversation_id: str
    ) -> Optional[Conversation]:
        """Get a conversation by ID"""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_conversation(
        self,
        conversation_id: str,
        session_id: str
    ) -> Conversation:
        """Create a new conversation"""
        stmt = insert(Conversation).values(
            id=conversation_id,
            session_id=session_id,
            created_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return await self._get_conversation_by_id(conversation_id)

    async def create_conversation(
        self,
        conversation: ConversationCreate
    ) -> Conversation:
        """Create a new conversation"""
        db_conversation = Conversation(
            session_id=conversation.session_id,
            title=conversation.title
        )
        self.db.add(db_conversation)
        await self.db.commit()
        await self.db.refresh(db_conversation)
        return db_conversation

    async def get_conversation(
        self,
        conversation_id: str,
        session_id: Optional[str] = None
    ) -> Optional[Conversation]:
        """Get a conversation by ID"""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        
        if session_id:
            query = query.where(Conversation.session_id == session_id)
            
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_conversations(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> List[ConversationSummary]:
        """List conversations for a session"""
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.session_id == session_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        conversations = result.scalars().all()
        
        return [
            ConversationSummary(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                message_count=len(conv.messages),
                last_message=conv.messages[-1].content if conv.messages else None
            )
            for conv in conversations
        ]

    async def update_conversation(
        self,
        conversation_id: str,
        update_data: ConversationUpdate,
        session_id: Optional[str] = None
    ) -> Optional[Conversation]:
        """Update a conversation"""
        conversation = await self.get_conversation(conversation_id, session_id)
        if not conversation:
            return None
            
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(conversation, field, value)
            
        if update_data.is_shared and not conversation.share_url:
            conversation.share_url = str(uuid.uuid4())
            
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def add_message(
        self,
        conversation_id: str,
        message: MessageCreate,
        session_id: Optional[str] = None
    ) -> Optional[Message]:
        """Add a message to a conversation"""
        # Get conversation
        conversation = await self.get_conversation(conversation_id, session_id)
        if not conversation:
            return None
            
        # Create message
        db_message = Message(
            conversation_id=conversation_id,
            role=message.role,
            content=message.content,
            created_at=datetime.utcnow(),
            clip_path=message.clip_metadata.clip_path if message.clip_metadata else None,
            clip_url=message.clip_url,
            subtitle_url=message.subtitle_url,
            clip_start_time=message.clip_metadata.start_time if message.clip_metadata else None,
            clip_end_time=message.clip_metadata.end_time if message.clip_metadata else None,
            clip_character=message.clip_metadata.character if message.clip_metadata else None,
            clip_episode=message.clip_metadata.episode if message.clip_metadata else None,
            clip_season=int(float(message.clip_metadata.season)) if message.clip_metadata and message.clip_metadata.season else None,
            clip_confidence=message.clip_metadata.confidence if message.clip_metadata else None
        )
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        self.db.add(db_message)
        await self.db.commit()
        await self.db.refresh(db_message)
        
        return db_message

    async def delete_conversation(
        self,
        conversation_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """Delete a conversation"""
        conversation = await self.get_conversation(conversation_id, session_id)
        if not conversation:
            return False
            
        await self.db.delete(conversation)
        await self.db.commit()
        return True

    async def create_conversation_from_messages(
        self,
        messages: List[Dict[str, Any]],
        session_id: str
    ) -> Conversation:
        """Create a new conversation from a list of messages"""
        # Create conversation
        conversation_id = str(uuid.uuid4())
        conversation = await self._create_conversation(conversation_id, session_id)
        
        # Add all messages
        for msg in messages:
            clip_metadata = msg.get('clip_metadata')
            db_message = Message(
                conversation_id=conversation_id,
                role=msg['role'],
                content=msg['content'],
                created_at=datetime.utcnow(),
                clip_path=clip_metadata.get('clip_path') if clip_metadata else None,
                clip_url=msg.get('clip_url'),
                subtitle_url=msg.get('subtitle_url'),
                clip_start_time=clip_metadata.get('start_time') if clip_metadata else None,
                clip_end_time=clip_metadata.get('end_time') if clip_metadata else None,
                clip_character=clip_metadata.get('character') if clip_metadata else None,
                clip_episode=clip_metadata.get('episode') if clip_metadata else None,
                clip_season=int(float(clip_metadata.get('season'))) if clip_metadata and clip_metadata.get('season') else None,
                clip_confidence=clip_metadata.get('confidence') if clip_metadata else None,
                message_metadata=clip_metadata
            )
            self.db.add(db_message)
        
        # Set conversation as shared
        conversation.is_shared = True
        conversation.share_url = str(uuid.uuid4())
        
        await self.db.commit()
        await self.db.refresh(conversation)
        
        return conversation 