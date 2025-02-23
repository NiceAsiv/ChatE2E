from dataclasses import dataclass, asdict
from typing import Optional, Dict , List
from chate2e.model.message import Message

class MessageManager:
    """消息管理"""
    def __init__(self):
        self.messages: Dict[str, List[Message]] = {}  # user_id -> messages
        self.offline_messages: Dict[str, List[Message]] = {}  # user_id -> messages
        
    def add_message(self, message: Message) -> None:
        """添加消息到历史记录"""
        if message.header.receiver_id not in self.messages:
            self.messages[message.header.receiver_id] = []
        self.messages[message.header.receiver_id].append(message)
        
    def get_session_messages(self, session_id: str) -> List[Message]:
        """获取会话的所有消息"""
        return self.messages.get(session_id, [])
        
    def add_offline_message(self, message: Message) -> None:
        """添加离线消息"""
        if message.header.receiver_id not in self.offline_messages:
            self.offline_messages[message.header.receiver_id] = []
        self.offline_messages[message.header.receiver_id].append(message)
        
    def get_offline_messages(self, user_id: str) -> List[Message]:
        """获取并清空用户的离线消息"""
        messages = self.offline_messages.get(user_id, [])
        if user_id in self.offline_messages:
            del self.offline_messages[user_id]
        return messages

    def get_recent_messages(self, user_id: str) -> List[Message]:
        """获取最近的消息"""
        return self.get_session_messages(user_id)