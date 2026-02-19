"""
Agent 聊天路由
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from sqlalchemy.orm import Session as DBSession
from db.database import get_db
from services import storage
from services.agent_service import process_message

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    history: list[dict] = []


@router.post("/chat")
async def chat(body: ChatRequest, db: DBSession = Depends(get_db)):
    """同步聊天端点"""
    # 保存用户消息
    storage.save_chat_message(db, body.conversation_id, "user", body.message)

    # Agent 处理
    response = process_message(db, body.message, body.history)

    # 保存 assistant 回复
    storage.save_chat_message(
        db, body.conversation_id, "assistant", response.content,
        tool_calls=response.tool_calls,
    )

    return {
        "conversation_id": body.conversation_id,
        "role": "assistant",
        "content": response.content,
        "tool_calls": response.tool_calls,
    }


@router.get("/history/{conversation_id}")
async def get_history(conversation_id: str, db: DBSession = Depends(get_db)):
    """获取对话历史"""
    messages = storage.list_chat_messages(db, conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}


@router.get("/conversations")
async def get_conversations(db: DBSession = Depends(get_db)):
    """列出最近对话"""
    conversations = storage.list_conversations(db)
    return {"conversations": conversations}
