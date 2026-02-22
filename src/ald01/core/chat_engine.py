"""
ALD-01 Chat Engine
AGI-like conversational experience — manages conversations, integrates with
brain, modes, multi-model, voice, and tool execution.
"""

import os
import time
import uuid
import json
import asyncio
import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass, field

from ald01 import CONFIG_DIR, DATA_DIR

logger = logging.getLogger("ald01.chat_engine")


@dataclass
class ChatMessage:
    """A single chat message."""
    id: str
    role: str  # 'user', 'assistant', 'system', 'tool'
    content: str
    conversation_id: str
    timestamp: float = field(default_factory=time.time)
    agent: str = ""
    model: str = ""
    tokens_used: int = 0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    thinking: List[str] = field(default_factory=list)
    voice_url: str = ""  # Path to TTS audio file if voice enabled
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "agent": self.agent,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "tool_calls": self.tool_calls,
            "thinking": self.thinking,
            "voice_url": self.voice_url,
            "metadata": self.metadata,
        }


@dataclass
class Conversation:
    """A conversation thread."""
    id: str
    title: str = "New Chat"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[ChatMessage] = field(default_factory=list)
    mode: str = "default"
    agent: str = "general"
    pinned: bool = False
    archived: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_messages: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
            "mode": self.mode,
            "agent": self.agent,
            "pinned": self.pinned,
            "archived": self.archived,
        }
        if include_messages:
            data["messages"] = [m.to_dict() for m in self.messages]
        return data


class ChatEngine:
    """
    Core chat engine for AGI-like conversational experience.
    
    Features:
    - New chat / continue conversation
    - All chats saved to backend (data/normal/conversations/)
    - Brain skill activation on each interaction
    - Mode-aware system prompts
    - Multi-model support
    - Voice response option (text + voice simultaneously)
    - Tool execution within chat
    - Streaming support
    """

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._active_conversation_id: Optional[str] = None
        self._voice_enabled: bool = False
        self._conversations_dir = os.path.join(DATA_DIR, "normal", "conversations")
        os.makedirs(self._conversations_dir, exist_ok=True)
        self._load_conversations()

    @property
    def voice_enabled(self) -> bool:
        return self._voice_enabled

    @voice_enabled.setter
    def voice_enabled(self, value: bool):
        self._voice_enabled = value

    def new_conversation(self, title: str = "", agent: str = "general") -> Conversation:
        """Create a new conversation."""
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        conv = Conversation(
            id=conv_id,
            title=title or "New Chat",
            agent=agent,
        )
        self._conversations[conv_id] = conv
        self._active_conversation_id = conv_id
        self._save_conversation(conv)
        return conv

    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        return self._conversations.get(conv_id)

    def set_active_conversation(self, conv_id: str) -> bool:
        if conv_id in self._conversations:
            self._active_conversation_id = conv_id
            return True
        return False

    @property
    def active_conversation(self) -> Optional[Conversation]:
        if self._active_conversation_id:
            return self._conversations.get(self._active_conversation_id)
        return None

    def list_conversations(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """List all conversations, newest first."""
        convs = sorted(
            self._conversations.values(),
            key=lambda c: c.updated_at,
            reverse=True,
        )
        if not include_archived:
            convs = [c for c in convs if not c.archived]
        return [c.to_dict() for c in convs]

    def delete_conversation(self, conv_id: str) -> bool:
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            path = os.path.join(self._conversations_dir, f"{conv_id}.json")
            if os.path.exists(path):
                os.remove(path)
            if self._active_conversation_id == conv_id:
                self._active_conversation_id = None
            return True
        return False

    def archive_conversation(self, conv_id: str) -> bool:
        conv = self._conversations.get(conv_id)
        if conv:
            conv.archived = True
            self._save_conversation(conv)
            return True
        return False

    def pin_conversation(self, conv_id: str, pinned: bool = True) -> bool:
        conv = self._conversations.get(conv_id)
        if conv:
            conv.pinned = pinned
            self._save_conversation(conv)
            return True
        return False

    async def send_message(
        self,
        content: str,
        conversation_id: Optional[str] = None,
        agent: str = "",
    ) -> ChatMessage:
        """
        Send a user message and get AI response.
        Returns the assistant's response message.
        """
        # Get or create conversation
        conv = None
        if conversation_id:
            conv = self._conversations.get(conversation_id)
        if not conv:
            conv = self.new_conversation(title=content[:50])

        # Create user message
        user_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            role="user",
            content=content,
            conversation_id=conv.id,
        )
        conv.messages.append(user_msg)

        # Auto-title from first message
        if len(conv.messages) == 1:
            conv.title = self._generate_title(content)

        # Build context messages for LLM
        context_messages = self._build_context(conv, agent)

        # Get AI response
        assistant_msg = await self._get_ai_response(context_messages, conv, agent)
        conv.messages.append(assistant_msg)
        conv.updated_at = time.time()

        # Activate brain skills based on content
        self._activate_brain(content, assistant_msg.content)

        # Generate voice if enabled
        if self._voice_enabled:
            voice_path = await self._generate_voice(assistant_msg.content, conv.id, assistant_msg.id)
            assistant_msg.voice_url = voice_path

        # Save conversation
        self._save_conversation(conv)

        return assistant_msg

    async def stream_message(
        self,
        content: str,
        conversation_id: Optional[str] = None,
        agent: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream a response token by token."""
        conv = None
        if conversation_id:
            conv = self._conversations.get(conversation_id)
        if not conv:
            conv = self.new_conversation(title=content[:50])

        user_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            role="user",
            content=content,
            conversation_id=conv.id,
        )
        conv.messages.append(user_msg)

        if len(conv.messages) == 1:
            conv.title = self._generate_title(content)

        context_messages = self._build_context(conv, agent)

        # Stream from provider
        full_response = ""
        try:
            from ald01.providers.manager import get_provider_manager
            pm = get_provider_manager()
            async for chunk in pm.stream_completion(context_messages):
                full_response += chunk
                yield chunk
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            full_response = error_msg
            yield error_msg

        # Save the complete assistant message
        assistant_msg = ChatMessage(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            role="assistant",
            content=full_response,
            conversation_id=conv.id,
        )
        conv.messages.append(assistant_msg)
        conv.updated_at = time.time()
        self._activate_brain(content, full_response)
        self._save_conversation(conv)

    def _build_context(self, conv: Conversation, agent: str = "") -> List[Dict[str, str]]:
        """Build message context for the LLM."""
        messages = []

        # System prompt
        system_prompt = self._get_system_prompt(agent or conv.agent)
        messages.append({"role": "system", "content": system_prompt})

        # Conversation history (last 30 messages for context window)
        for msg in conv.messages[-30:]:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

        return messages

    def _get_system_prompt(self, agent: str = "general") -> str:
        """Get system prompt based on current mode and agent."""
        base_prompt = (
            "You are ALD-01, an Advanced Local Desktop Intelligence agent. "
            "You are a powerful AGI-like AI assistant that can help with coding, "
            "research, analysis, and any task the user needs. "
            "You are professional, helpful, and knowledgeable. "
            "You have access to tools for file operations, terminal, code execution, "
            "and web browsing. Always provide thorough, accurate answers. "
            "When asked to write code, write production-quality code. "
        )

        # Add mode-specific instructions
        try:
            from ald01.core.modes import get_mode_manager
            mm = get_mode_manager()
            mode_prompt = mm.get_mode_enhanced_prompt()
            if mode_prompt:
                base_prompt += f"\n\n{mode_prompt}"
        except Exception:
            pass

        # Add localization
        try:
            from ald01.core.localization import get_localization
            loc = get_localization()
            if loc.current_language != "en":
                if loc.current_language == "hi":
                    base_prompt += "\n\nUser prefers Hindi. Respond in Hindi (Devanagari script)."
                elif loc.current_language == "hinglish":
                    base_prompt += "\n\nUser prefers Hinglish. Respond in a mix of Hindi and English."
        except Exception:
            pass

        return base_prompt

    async def _get_ai_response(
        self,
        messages: List[Dict[str, str]],
        conv: Conversation,
        agent: str = "",
    ) -> ChatMessage:
        """Get AI response from provider."""
        try:
            from ald01.providers.manager import get_provider_manager
            pm = get_provider_manager()
            result = await pm.chat_completion(messages)

            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            model = result.get("model", "unknown")
            tokens = result.get("usage", {}).get("total_tokens", 0)

            return ChatMessage(
                id=f"msg_{uuid.uuid4().hex[:10]}",
                role="assistant",
                content=content,
                conversation_id=conv.id,
                model=model,
                tokens_used=tokens,
                agent=agent or conv.agent,
            )
        except Exception as e:
            logger.error(f"AI response error: {e}")
            return ChatMessage(
                id=f"msg_{uuid.uuid4().hex[:10]}",
                role="assistant",
                content=f"I encountered an error: {str(e)}. Please check your provider setup with `ald-01 doctor`.",
                conversation_id=conv.id,
                agent=agent or conv.agent,
            )

    async def _generate_voice(self, text: str, conv_id: str, msg_id: str) -> str:
        """Generate TTS voice for a message."""
        try:
            voice_dir = os.path.join(DATA_DIR, "temp", "voice")
            os.makedirs(voice_dir, exist_ok=True)
            voice_path = os.path.join(voice_dir, f"{msg_id}.wav")

            # Try pyttsx3 for local TTS
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty('rate', 180)
                engine.save_to_file(text[:500], voice_path)  # Limit length
                engine.runAndWait()
                return f"/api/voice/{msg_id}.wav"
            except ImportError:
                pass

            # Fallback: try edge-tts
            try:
                import edge_tts
                communicate = edge_tts.Communicate(text[:500], "en-IN-NeerjaNeural")
                await communicate.save(voice_path)
                return f"/api/voice/{msg_id}.wav"
            except ImportError:
                pass

            return ""
        except Exception as e:
            logger.debug(f"Voice generation failed: {e}")
            return ""

    def _activate_brain(self, user_input: str, response: str) -> None:
        """Activate brain skills based on conversation content."""
        try:
            from ald01.core.brain import get_brain
            brain = get_brain()

            combined = (user_input + " " + response).lower()

            # Detect skills
            skill_keywords = {
                "python": "skill_python", "javascript": "skill_javascript",
                "html": "skill_web", "css": "skill_web", "react": "skill_web",
                "api": "skill_api", "rest": "skill_api", "graphql": "skill_api",
                "database": "skill_database", "sql": "skill_database", "postgres": "skill_database",
                "docker": "skill_devops", "kubernetes": "skill_devops", "ci/cd": "skill_devops",
                "security": "skill_security", "vulnerability": "skill_security",
                "test": "skill_testing", "unittest": "skill_testing", "pytest": "skill_testing",
                "debug": "skill_debugging", "error": "skill_debugging", "bug": "skill_debugging",
                "architecture": "skill_architecture", "design pattern": "skill_architecture",
                "machine learning": "skill_ml", "neural": "skill_ml", "model": "skill_ml",
                "data": "skill_data", "pandas": "skill_data", "analysis": "skill_data",
                "linux": "skill_linux", "terminal": "skill_linux", "bash": "skill_linux",
                "cloud": "skill_cloud", "aws": "skill_cloud", "azure": "skill_cloud",
                "mobile": "skill_mobile", "flutter": "skill_mobile", "react native": "skill_mobile",
            }

            for keyword, skill_id in skill_keywords.items():
                if keyword in combined:
                    brain.activate_skill(skill_id, 0.03)

            # Always activate reasoning
            brain.activate_reasoning("cot")
            brain.activate_skill("aptitude_communication", 0.01)

        except Exception:
            pass

    def _generate_title(self, first_message: str) -> str:
        """Generate a conversation title from first message."""
        title = first_message.strip()[:60]
        title = re.sub(r'\s+', ' ', title)
        if len(first_message) > 60:
            title += "..."
        return title or "New Chat"

    def get_messages(self, conv_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        conv = self._conversations.get(conv_id)
        if not conv:
            return []
        return [m.to_dict() for m in conv.messages[-limit:]]

    def search_conversations(self, query: str) -> List[Dict[str, Any]]:
        """Search conversations by content."""
        query_lower = query.lower()
        results = []
        for conv in self._conversations.values():
            # Search title
            if query_lower in conv.title.lower():
                results.append(conv.to_dict())
                continue
            # Search messages
            for msg in conv.messages:
                if query_lower in msg.content.lower():
                    results.append(conv.to_dict())
                    break
        return results

    def get_stats(self) -> Dict[str, Any]:
        total_msgs = sum(len(c.messages) for c in self._conversations.values())
        return {
            "total_conversations": len(self._conversations),
            "total_messages": total_msgs,
            "active_conversation": self._active_conversation_id,
            "voice_enabled": self._voice_enabled,
            "archived": sum(1 for c in self._conversations.values() if c.archived),
        }

    def _save_conversation(self, conv: Conversation) -> None:
        """Save conversation to file."""
        try:
            path = os.path.join(self._conversations_dir, f"{conv.id}.json")
            data = conv.to_dict(include_messages=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Conversation save failed: {e}")

    def _load_conversations(self) -> None:
        """Load all conversations from disk."""
        try:
            if not os.path.exists(self._conversations_dir):
                return
            for f in os.listdir(self._conversations_dir):
                if not f.endswith(".json"):
                    continue
                path = os.path.join(self._conversations_dir, f)
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    messages = [
                        ChatMessage(
                            id=m.get("id", ""),
                            role=m.get("role", ""),
                            content=m.get("content", ""),
                            conversation_id=data.get("id", ""),
                            timestamp=m.get("timestamp", 0),
                            agent=m.get("agent", ""),
                            model=m.get("model", ""),
                            tokens_used=m.get("tokens_used", 0),
                            voice_url=m.get("voice_url", ""),
                        )
                        for m in data.get("messages", [])
                    ]
                    conv = Conversation(
                        id=data.get("id", f.replace(".json", "")),
                        title=data.get("title", ""),
                        created_at=data.get("created_at", 0),
                        updated_at=data.get("updated_at", 0),
                        messages=messages,
                        mode=data.get("mode", "default"),
                        agent=data.get("agent", "general"),
                        pinned=data.get("pinned", False),
                        archived=data.get("archived", False),
                    )
                    self._conversations[conv.id] = conv
                except Exception as e:
                    logger.debug(f"Skipping corrupt conversation: {f}: {e}")
        except Exception as e:
            logger.warning(f"Conversation load failed: {e}")


_chat_engine: Optional[ChatEngine] = None

def get_chat_engine() -> ChatEngine:
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = ChatEngine()
    return _chat_engine
