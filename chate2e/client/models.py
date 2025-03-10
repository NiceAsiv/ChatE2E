from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional , Tuple
from datetime import datetime, timezone
from chate2e.model.bundle import Bundle, LocalBundle
import hashlib
from base64 import b64encode

import json
import os
import uuid
from chate2e.model.message import Message
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
    password_hash: Optional[str] = None  # 密码哈希值
    salt: Optional[str] = None  # 密码哈希盐值
    bundle: Optional[Bundle] = None  # 密钥Bundle
    localBundle: Optional[LocalBundle] = None  # 本地密钥Bundle
    
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
    
    @staticmethod
    def _hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """密码加密"""
        if not salt:
            salt = b64encode(os.urandom(16)).decode('utf-8')
        pw_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode(), 
            salt.encode(), 
            100000
        )
        return b64encode(pw_hash).decode('utf-8'), salt
    
    def set_password(self, password: str):
        """设置密码"""
        self.password_hash, self.salt = self._hash_password(password)
        
    def verify_password(self, password: str) -> bool:
        """验证密码"""
        if not self.password_hash or not self.salt:
            return False
        pw_hash, _ = self._hash_password(password, self.salt)
        return pw_hash == self.password_hash
    
    def set_bundle(self, bundle: Bundle):
        """设置Signal Bundle"""
        if isinstance(bundle, Bundle):
            self.bundle = bundle  # 直接存储Bundle对象
        else:
            raise ValueError("bundle must be a Bundle instance")

    def set_local_bundle(self, localBundle: LocalBundle):
        """设置Signal Bundle"""
        if isinstance(localBundle, LocalBundle):
            self.localBundle = localBundle
        else:
            raise ValueError("localBundle must be a LocalBundle instance")

    def get_local_bundle(self) -> Optional[LocalBundle]:
        """获取Signal Bundle"""
        return self.localBundle  # 直接返回Bundle对象
        
    def get_bundle(self) -> Optional[Bundle]:
        """获取Signal Bundle"""
        return self.bundle  # 直接返回Bundle对象
    
    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'avatar_path': self.avatar_path,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat(),
            'password_hash': self.password_hash,
            'salt': self.salt,
            'bundle': self.bundle.to_dict() if self.bundle else None,  # Bundle对象转字典
            'localBundle': self.localBundle.to_dict() if self.localBundle else None,
            'friends': [friend.to_dict() for friend in self.friends]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserProfile':
        bundle_data = data.get('bundle')
        bundle = Bundle.from_dict(bundle_data) if bundle_data else None

        local_bundle_data = data.get('localBundle')
        local_bundle = LocalBundle.from_dict(local_bundle_data) if local_bundle_data else None
        
        return cls(
            user_id=data['user_id'],
            username=data['username'],
            avatar_path=data['avatar_path'],
            status=UserStatus.from_str(data['status']),
            last_seen=datetime.fromisoformat(data['last_seen']),
            password_hash=data.get('password_hash'),
            salt=data.get('salt'),
            bundle=bundle,
            localBundle=local_bundle,
            friends=[Friend.from_dict(friend_data) for friend_data in data.get('friends', [])]
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
    def __init__(self, user_id: Optional[str] = None, base_dir: str = "chat_data"):
        self.base_dir = base_dir
        self.useruuid = user_id
        
        # 初始化数据
        self.user: Optional[UserProfile] = None
        self.sessions: Dict[str, ChatSession] = {}
        
        # 如果有用户ID，加载用户数据
        if user_id:
            self.user_data_dir = os.path.join(base_dir, user_id)
            self.user_file = os.path.join(self.user_data_dir, "user_profile.json")
            self.sessions_file = os.path.join(self.user_data_dir, "chat_sessions.json")
            os.makedirs(self.user_data_dir, exist_ok=True)
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

    def register_user(self, username: str, password: str, user_uuid: str, bundle: Bundle ,local_bundle: LocalBundle) -> bool:
        """注册新用户"""
        try:
            # 更新用户ID相关路径
            self.useruuid = user_uuid
            self.user_data_dir = os.path.join(self.base_dir, user_uuid)
            self.user_file = os.path.join(self.user_data_dir, "user_profile.json")
            self.sessions_file = os.path.join(self.user_data_dir, "chat_sessions.json")
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            # 创建新用户档案
            user = UserProfile(
                user_id=user_uuid,
                username=username,
                avatar_path=os.path.join(UserProfile.AVATAR_DIR, UserProfile.DEFAULT_AVATAR),
                status=UserStatus.OFFLINE
            )
            
            # 设置密码和Bundle
            user.set_password(password)
            user.set_bundle(bundle)
            user.set_local_bundle(local_bundle)
            
            # 保存用户数据
            self.user = user
            self.save_data()
            return True
            
        except Exception as e:
            print(f"注册用户失败: {e}")
            return False
            
    def verify_user(self, username: str, password: str) -> Optional[str]:
        """验证用户登录"""
        try:
            # 遍历chat_data目录查找用户
            if not os.path.exists(self.base_dir):
                return None
                
            for user_dir in os.listdir(self.base_dir):
                profile_path = os.path.join(self.base_dir, user_dir, "user_profile.json")
                if os.path.exists(profile_path):
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        user_data = json.load(f)
                        if user_data['username'] == username:
                            # 找到用户，加载数据
                            self.useruuid = user_data['user_id']
                            self.user_data_dir = os.path.join(self.base_dir, self.useruuid)
                            self.user_file = os.path.join(self.user_data_dir, "user_profile.json")
                            self.sessions_file = os.path.join(self.user_data_dir, "chat_sessions.json")
                            self.user = UserProfile.from_dict(user_data)
                            
                            # 验证密码
                            if self.user.verify_password(password):
                                return self.user.user_id
                            break
            return None
            
        except Exception as e:
            print(f"验证用户失败: {e}")
            return None

    def get_bundle(self) -> Optional[Bundle]:
        """获取用户的Bundle"""
        if self.user:
            return self.user.get_bundle()
        return None

    def get_local_bundle(self) -> Optional[LocalBundle]:
        """获取用户的Bundle"""
        if self.user:
            return self.user.get_local_bundle()
        return None
                
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
