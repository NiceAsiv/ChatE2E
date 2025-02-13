from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from datetime import datetime
import json
import os
import uuid
import time

@dataclass
class UserProfile:
    """用户信息类"""
    user_id: str
    username: str
    avatar_path: str
    status: str = "offline"  # online/offline/away
    last_seen: str = ""
    contacts: List[str] = field(default_factory=list)  # 联系人ID列表

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'UserProfile':
        return cls(**data)


@dataclass
class ChatSession:
    session_id: str  # uuid
    participant1_id: str
    participant2_id: str
    last_message: Optional[Dict] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        return cls(**data)


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


class DataManager:
    """数据管理类"""

    def __init__(self, data_dir: str = "chat_data"):
        self.data_dir = data_dir
        self.users_file = os.path.join(data_dir, "users.json")
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self.messages_dir = os.path.join(data_dir, "messages")

        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.messages_dir, exist_ok=True)

        # 初始化数据
        self.users: Dict[str, UserProfile] = {}
        self.sessions: Dict[str, ChatSession] = {}
        self.load_data()

    def load_data(self):
        """加载所有数据"""
        # 加载用户数据
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                self.users = {
                    uid: UserProfile.from_dict(data)
                    for uid, data in users_data.items()
                }

        # 加载会话数据
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                self.sessions = {
                    sid: ChatSession.from_dict(data)
                    for sid, data in sessions_data.items()
                }

    def save_data(self):
        """保存所有数据"""
        # 保存用户数据
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump({
                uid: user.to_dict()
                for uid, user in self.users.items()
            }, f, ensure_ascii=False, indent=2)

        # 保存会话数据
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump({
                sid: session.to_dict()
                for sid, session in self.sessions.items()
            }, f, ensure_ascii=False, indent=2)

    def get_or_create_session(self, user1_id: str, user2_id: str) -> ChatSession:
        """获取或创建两个用户之间的会话"""
        # 确保用户ID顺序一致，避免重复会话
        participant_ids = sorted([user1_id, user2_id])

        # 查找现有会话
        for session in self.sessions.values():
            if sorted([session.participant1_id, session.participant2_id]) == participant_ids:
                return session

        # 创建新会话
        session = ChatSession(
            session_id=str(uuid.uuid4()),
            participant1_id=participant_ids[0],
            participant2_id=participant_ids[1]
        )
        self.sessions[session.session_id] = session
        self.save_data()
        return session

    def save_message(self, message: Message):
        """保存消息"""
        messages = self.load_messages(message.session_id)
        messages.append(message)
        self._save_session_messages(message.session_id, messages)

        # 更新会话的最后消息和活动时间
        if message.session_id in self.sessions:
            session = self.sessions[message.session_id]
            session.last_message = message.to_dict()
            session.last_active = message.timestamp
            self.save_data()

    def load_messages(self, session_id: str) -> List[Message]:
        """加载会话消息"""
        messages_file = os.path.join(self.messages_dir, f"{session_id}.json")
        if not os.path.exists(messages_file):
            return []

        with open(messages_file, 'r', encoding='utf-8') as f:
            messages_data = json.load(f)
            return [Message.from_dict(msg_data) for msg_data in messages_data]

    def _save_session_messages(self, session_id: str, messages: List[Message]):
        """保存会话消息"""
        messages_file = os.path.join(self.messages_dir, f"{session_id}.json")
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump([msg.to_dict() for msg in messages], f,
                      ensure_ascii=False, indent=2)

    def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """获取用户的所有会话"""
        return [
            session for session in self.sessions.values()
            if user_id in [session.participant1_id, session.participant2_id]
        ]


def create_sample_data():
    data_manager = DataManager()

    # 创建示例用户
    alice = UserProfile(
        user_id="u001",
        username="Alice",
        avatar_path="assets/avatars/alice.png",
        public_key="alice_public_key",
        status="online",
        contacts=["u002"]
    )

    bob = UserProfile(
        user_id="u002",
        username="Bob",
        avatar_path="assets/avatars/bob.png",
        public_key="bob_public_key",
        status="offline",
        contacts=["u001"]
    )

    # 保存用户
    data_manager.users[alice.user_id] = alice
    data_manager.users[bob.user_id] = bob

    # 创建会话
    session = data_manager.get_or_create_session(alice.user_id, bob.user_id)

    # 创建消息
    message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        sender_id=alice.user_id,
        receiver_id=bob.user_id,
        content="Hello Bob!",
        encryption={
            "algorithm": "AES-GCM",
            "iv": "random_iv_here",
            "tag": "auth_tag_here"
        }
    )

    # 保存消息
    data_manager.save_message(message)


if __name__ == "__main__":
    create_sample_data()