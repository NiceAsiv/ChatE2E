from dataclasses import dataclass, asdict
from typing import Optional, Dict , List
import time
import json
import uuid

@dataclass
class Message:
    message_id: str
    session_id: str
    sender_id: str
    receiver_id: str
    encrypted_content: str
    timestamp: float = time.time()
    encryption: Optional[Dict] = None  # 存储加密相关信息,如ratchet key等
    
    def to_dict(self) -> dict:
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(**data)
        
    def serialize(self) -> str:
        return json.dumps(self.to_dict())
        
    @classmethod
    def deserialize(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls.from_dict(data)

    @staticmethod
    def generate_id() -> str:
        """生成消息ID"""
        return str(uuid.uuid4())

class SessionManager:
    """会话管理"""
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}  # session_id -> session info
        
    def create_session(self, sender_id: str, receiver_id: str) -> str:
        """创建新的会话"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'created_at': time.time(),
            'last_active': time.time(),
            'participants': [sender_id, receiver_id]
        }
        return session_id
        
    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话信息"""
        return self.sessions.get(session_id)
        
    def update_session_activity(self, session_id: str) -> None:
        """更新会话最后活动时间"""
        if session_id in self.sessions:
            self.sessions[session_id]['last_active'] = time.time()
            
    def get_user_sessions(self, user_id: str) -> List[str]:
        """获取用户参与的所有会话"""
        return [
            session_id 
            for session_id, info in self.sessions.items()
            if user_id in info['participants']
        ]

class MessageManager:
    """消息管理"""
    def __init__(self):
        self.messages: Dict[str, List[Message]] = {}  # session_id -> messages
        self.offline_messages: Dict[str, List[Message]] = {}  # user_id -> messages
        
    def add_message(self, message: Message) -> None:
        """添加消息到会话历史"""
        if message.session_id not in self.messages:
            self.messages[message.session_id] = []
        self.messages[message.session_id].append(message)
        
    def get_session_messages(self, session_id: str) -> List[Message]:
        """获取会话的所有消息"""
        return self.messages.get(session_id, [])
        
    def add_offline_message(self, message: Message) -> None:
        """添加离线消息"""
        if message.receiver_id not in self.offline_messages:
            self.offline_messages[message.receiver_id] = []
        self.offline_messages[message.receiver_id].append(message)
        
    def get_offline_messages(self, user_id: str) -> List[Message]:
        """获取并清空用户的离线消息"""
        messages = self.offline_messages.get(user_id, [])
        self.offline_messages[user_id] = []
        return messages