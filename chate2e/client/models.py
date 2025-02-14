from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from datetime import datetime, timezone

import json
import os
import uuid
from chate2e.utils.message import Message
import enum

class UserStatus(enum.Enum):
    """用户状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"

    @classmethod
    def from_str(cls, status: str) -> 'UserStatus':
        """从字符串转换为状态枚举"""
        try:
            return cls(status.lower())
        except ValueError:
            return cls.OFFLINE

@dataclass
class Friend:
    """好友类"""
    user_id: str
    username: str
    avatar_path: str
    status: UserStatus = field(default=UserStatus.OFFLINE)
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = UserStatus.from_str(self.status)

    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'avatar_path': self.avatar_path,
            'status': self.status.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Friend':
        return cls(
            user_id=data['user_id'],
            username=data['username'],
            avatar_path=data['avatar_path'],
            status=UserStatus.from_str(data['status'])
        )


@dataclass
class UserProfile:
    """用户信息类"""
    user_id: str
    username: str
    avatar_path: str
    status: UserStatus = field(default=UserStatus.OFFLINE)  # 用户状态
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))  # 最后在线时间
    friends: List[Friend] = field(default_factory=list)  # 好友列表
    
    AVATAR_DIR = "assets/avatars"
    DEFAULT_AVATAR = "default.png"
    
    
    def __post_init__(self):
        # 状态处理
        if isinstance(self.status, str):
            self.status = UserStatus.from_str(self.status)
        
        # 确保头像路径存在
        if not os.path.exists(self.avatar_path):
            self.avatar_path = os.path.join(self.AVATAR_DIR, self.DEFAULT_AVATAR)
        
    @property
    def is_online(self) -> bool:
        return self.status == UserStatus.ONLINE
    
    def update_status(self, new_status: UserStatus):
        """更新用户状态"""
        self.status = new_status
        self.last_seen = datetime.now(timezone.utc)
    
    def add_friend(self, friend: Friend) -> bool:
        """添加好友"""
        if not any(f.user_id == friend.user_id for f in self.friends):
            self.friends.append(friend)
            return True
        return False
    
    def remove_friend(self, friend_id: str) -> bool:
        """移除好友"""
        initial_length = len(self.friends)
        self.friends = [f for f in self.friends if f.user_id != friend_id]
        return len(self.friends) < initial_length
    
    def get_friend(self, friend_id: str) -> Optional[Friend]:
        """获取指定好友"""
        return next((f for f in self.friends if f.user_id == friend_id), None)
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'avatar_path': self.avatar_path,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat(),
            'friends': [friend.to_dict() for friend in self.friends]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserProfile':
        return cls(
            user_id=data['user_id'],
            username=data['username'],
            avatar_path=data['avatar_path'],
            status=UserStatus.from_str(data['status']),
            last_seen=data['last_seen'],
            friends=[Friend.from_dict(friend_data) for friend_data in data['friends']]
        )

@dataclass
class ChatSession:
    """聊天会话类"""
    participant1_id: str 
    participant2_id: str 
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    last_message: Optional[Message] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages: List[Message] = field(default_factory=list)
    
    
    def __post_init__(self):
        # 确保participant_ids是有序的，避免重复会话
        if self.participant1_id > self.participant2_id:
            self.participant1_id, self.participant2_id = (
                self.participant2_id, self.participant1_id
            )
            
        # 时间处理
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.last_active, str):
            self.last_active = datetime.fromisoformat(self.last_active)
    
    @property
    def participants(self) -> List[str]:
        """获取参与者ID列表"""
        return [self.participant1_id, self.participant2_id]
    
    def has_participant(self, user_id: str) -> bool:
        """检查用户是否是会话参与者"""
        return user_id in self.participants
    
    def get_other_participant(self, user_id: str) -> Optional[str]:
        """获取另一个参与者的ID"""
        if not self.has_participant(user_id):
            return None
        return (
            self.participant2_id 
            if user_id == self.participant1_id 
            else self.participant1_id
        )
    
    def update_last_message(self, message: Message):
        """更新最后一条消息"""
        self.last_message = message
        self.last_active = datetime.now(timezone.utc)
    
    def add_message(self, message: Message):
        """添加消息"""
        self.messages.append(message)
        self.update_last_message(message)
    
    def to_dict(self) -> dict:
        return {
            'session_id': self.session_id,
            'participant1_id': self.participant1_id,
            'participant2_id': self.participant2_id,
            'last_message': self.last_message.to_dict() if self.last_message else None,
            'created_at': self.created_at.isoformat(),
            'last_active': self.last_active.isoformat(),
            'messages': [msg.to_dict() for msg in self.messages]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        messages_data = data.get('messages', [])
        messages = [Message.from_dict(msg_data) for msg_data in messages_data]
        
        return cls(
            participant1_id=data['participant1_id'],
            participant2_id=data['participant2_id'],
            session_id=data['session_id'],
            last_message=Message.from_dict(data['last_message']) if data['last_message'] else None,
            created_at=data['created_at'],
            last_active=data['last_active'],
            messages=messages
        )

class DataManager:
    """数据管理类"""

    def __init__(self, user_id, base_dir: str = "chat_data"):
        self.useruuid = user_id
        self.user_data_dir = os.path.join(base_dir, user_id)
        self.user_file = os.path.join(base_dir, user_id, "user_profile.json")
        self.sessions_file = os.path.join(base_dir, user_id, "chat_sessions.json")
        
        #确保目录存在
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        # 初始化数据
        self.user: UserProfile = None
        self.sessions: Dict[str, ChatSession] = {}
        
        # 加载数据
        self.load_data()
    
    def load_data(self):
        """加载所有数据"""
        # 加载用户数据
        if os.path.exists(self.user_file):
            with open(self.user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
                self.user = UserProfile.from_dict(user_data)
        
        # 加载会话数据
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                self.sessions = {
                    session_data['session_id']: ChatSession.from_dict(session_data)
                    for session_data in sessions_data
                }
                
    def set_user(self, user: UserProfile):
        """设置用户数据"""
        self.user = user
        self.save_data()
        
    def add_message(self, session_id: str, message: Message):
        """添加消息到指定会话"""
        if session_id in self.sessions:
            self.sessions[session_id].add_message(message)
            self.save_data()
        else:
            print(f"会话 {session_id} 不存在！")    
    
    def add_friend(self, friend: Friend):
        """添加好友"""
        if self.user:
            if self.user.add_friend(friend):
                self.save_data()
        
    def save_data(self):
        """保存所有数据"""
        # 保存用户数据
        with open(self.user_file, 'w', encoding='utf-8') as f:
            json.dump(self.user.to_dict(), f, ensure_ascii=False, indent=2)
            
        # 保存会话数据
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(
                [session.to_dict() for session in self.sessions.values()],
                f, ensure_ascii=False, indent=2
            )

    def get_or_create_session(self, user2_id: str) -> ChatSession:
        """获取或创建两个用户之间的会话"""
        # 确保用户ID顺序一致，避免重复会话
        participant_ids = sorted([self.user.user_id, user2_id])

        # 查找现有会话
        for session in self.sessions.values():
            if sorted([session.participant1_id, session.participant2_id]) == participant_ids:
                return session

        # 创建新会话
        session = ChatSession(
            participant1_id=participant_ids[0],
            participant2_id=participant_ids[1]
        )
        self.sessions[session.session_id] = session
        self.save_data()
        return session
    
    def create_session_by_sender_session_id(self, session_id: str, user2_id: str) -> ChatSession:
        """根据发送者会话ID创建会话"""
        # 确保用户ID顺序一致，避免重复会话
        participant_ids = sorted([self.user.user_id, user2_id])

        # 创建新会话
        session = ChatSession(
            participant1_id=participant_ids[0],
            participant2_id=participant_ids[1]
        )
        session.session_id = session_id
        self.sessions[session_id] = session
        self.save_data()
        return session
    
    def get_last_message(self, user2_id: str) -> Message:
        """获取两个用户之间的最后一条消息"""
        if not self.user:
            return None
        participant_ids = sorted([self.user.user_id, user2_id])
        for session in self.sessions.values():
            if sorted([session.participant1_id, session.participant2_id]) == participant_ids:
                return session.last_message
        return None
        

from chate2e.utils.message import MessageType, Encryption


# 使用示例
def create_sample_data():
    # 创建数据管理器实例
    dm_alice = DataManager("u001")
    dm_bob = DataManager("u002")
    
    # 创建用户档案
    alice = UserProfile(
        user_id="u001",
        username="Alice",
        avatar_path="assets/avatars/alice.png",
        status=UserStatus.ONLINE
    )
    
    bob = UserProfile(
        user_id="u002",
        username="Bob",
        avatar_path="assets/avatars/bob.png",
        status=UserStatus.OFFLINE
    )
    
    # 保存用户信息
    dm_alice.set_user(alice)
    dm_bob.set_user(bob)
    
    # 添加好友关系
    dm_alice.add_friend(Friend.from_dict(bob.to_dict()))
    dm_bob.add_friend(Friend.from_dict(alice.to_dict()))
    
    # Alice 创建会话
    session = dm_alice.get_or_create_session(bob.user_id)
    
    # 创建初始化消息
    init_message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        sender_id=alice.user_id,
        receiver_id=bob.user_id,
        encrypted_content="Hello Bob!",
        message_type=MessageType.INITIATE,  # 使用INITIATE类型表示这是初始化消息
        encryption=Encryption(
            algorithm="AES-GCM",
            iv="alice_iv",
            tag="alice_tag"
        )
    )
    
    # 保存消息到 Alice 和 Bob 的聊天会话中
    dm_alice.add_message(session.session_id, init_message)

    # 模拟 Bob 接收到消息
    bob_session = dm_bob.create_session_by_sender_session_id(
        session_id=init_message.header.session_id,
        user2_id=alice.user_id
    )

    # Bob 接收并保存确认消息
    ack_message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        sender_id=bob.user_id,
        receiver_id=alice.user_id,
        encrypted_content="Hi Alice, got your message!",
        message_type=MessageType.ACK_INITIATE,  # 使用ACK_INITIATE类型表示这是确认消息
        encryption=Encryption(
            algorithm="AES-GCM",
            iv="bob_iv",
            tag="bob_tag"
        )
    )

    # 保存消息到 Bob 和 Alice 的聊天会话中
    dm_bob.add_message(bob_session.session_id, init_message)
    dm_bob.add_message(bob_session.session_id, ack_message)
    
    dm_alice.add_message(session.session_id, ack_message)

    print("示例数据创建成功！")

if __name__ == "__main__":
    create_sample_data()
