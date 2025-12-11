import json
import os
import uuid
from typing import Dict, Optional

from chate2e.model.bundle import Bundle
from chate2e.model.message import Message
from chate2e.server.socket_manager import socketio
from chate2e.server.user import User


def generate_short_uuid() -> str:
    """生成16位的UUID"""
    return uuid.uuid4().hex[:16]
            
class ChatServer:
    def __init__(self):
        self.users: Dict[str, User] = {}  # 用户ID -> 用户实例
        self.username_map: Dict[str, str] = {}  # username -> uuid
        self.socket_sessions: Dict[str, str] = {}  # socket_id -> user_id
        self.sessions: Dict[str, Dict] = {}  # session_id -> {participant1, participant2, created_at}
        self.user_sessions: Dict[str, Dict[str, str]] = {}  # user_id -> {peer_id -> session_id}
        
        # 设置数据目录路径
        self.server_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.server_dir, 'data')
        self.users_file = os.path.join(self.data_dir, 'users.json')
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        self._load_users()
    
    def add_socket_session(self, user_id: str, socket_id: str):
        """添加socket会话"""
        self.socket_sessions[socket_id] = user_id
        if user_id in self.users:
            self.users[user_id].is_online = True
    
    def remove_socket_session(self, socket_id: str):
        """移除socket会话"""
        if socket_id in self.socket_sessions:
            user_id = self.socket_sessions.pop(socket_id)
            if user_id in self.users:
                self.users[user_id].is_online = False
    
    def get_or_create_session(self, user1_id: str, user2_id: str) -> str:
        """获取或创建两个用户之间的会话ID
        
        Args:
            user1_id: 第一个用户ID
            user2_id: 第二个用户ID
            
        Returns:
            session_id: 会话ID
        """
        # 确保用户ID顺序一致
        participants = tuple(sorted([user1_id, user2_id]))
        
        # 检查是否已存在会话
        if user1_id in self.user_sessions:
            if user2_id in self.user_sessions[user1_id]:
                return self.user_sessions[user1_id][user2_id]
        
        # 创建新会话
        session_id = str(uuid.uuid4())
        
        # 存储会话信息
        self.sessions[session_id] = {
            'participants': participants,
            'created_at': None,  # 可以添加时间戳
            'user1_id': participants[0],
            'user2_id': participants[1]
        }
        
        # 建立双向映射
        if user1_id not in self.user_sessions:
            self.user_sessions[user1_id] = {}
        if user2_id not in self.user_sessions:
            self.user_sessions[user2_id] = {}
            
        self.user_sessions[user1_id][user2_id] = session_id
        self.user_sessions[user2_id][user1_id] = session_id
        
        print(f"[Server] 创建新会话: {session_id} for {user1_id} <-> {user2_id}")
        return session_id
    
    def validate_session(self, session_id: str, user_id: str) -> bool:
        """验证会话是否有效且用户有权访问
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 会话是否有效
        """
        if session_id not in self.sessions:
            return False
        
        session_info = self.sessions[session_id]
        return user_id in session_info['participants']

    def forward_message(self, message: Message) -> bool:
        """将消息转发给目标用户（定向发送）"""
        try:
            receiver_id = message.header.receiver_id
            
            # 查找接收者的socket连接
            receiver_socket_id = None
            for socket_id, user_id in self.socket_sessions.items():
                if user_id == receiver_id:
                    receiver_socket_id = socket_id
                    break
            
            if receiver_socket_id:
                # 定向发送给特定用户
                socketio.emit('new_message', message.to_dict(), room=receiver_socket_id)
                return True
            else:
                # TODO: 存储为离线消息
                return False
                
        except Exception as e:
            print(f"[Server] ✗ 消息转发失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_users(self) -> None:
        """加载用户信息"""
        # 从本地或者数据库加载用户信息
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data['users']:
                        user = User(user_data['username'], user_data['uuid'])
                        if user_data.get('bundle'):
                            user.bundle = Bundle.from_dict(user_data['bundle'])
                        self.users[user.uuid] = user
                        self.username_map[user.username] = user.uuid
                print(f"成功加载 {len(self.users)} 个用户")
        except Exception as e:
            print(f"加载用户数据失败: {e}")
    
    def _save_users(self) -> None:
        """保存用户信息"""
        try:
            data = {
                'users': [user.to_dict() for user in self.users.values()]
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"成功保存 {len(self.users)} 个用户")
        except Exception as e:
            print(f"保存用户数据失败: {e}")       
            
    def register_user(self, username: str, bundle_dict: dict) -> Optional[str]:
        """注册新用户"""
        if username in self.users:
            return None
        
        try:
            useruuid = generate_short_uuid()
            user = User(username, useruuid)
            user.set_bundle(Bundle.from_dict(bundle_dict))
            user.is_online = True
            self.users[useruuid] = user
            self.username_map[username] = useruuid
            self._save_users()
            return useruuid
        except Exception as e:
            print(f"注册用户失败: {e}")
            return None
        
    def is_user_registered(self, username: str) -> bool:
        """检查用户是否已注册"""
        return username in self.users
         
    def get_user_bundle_by_useruuid(self, useruuid: str) -> Optional[dict]:
        """获取用户的密钥Bundle"""
        if useruuid not in self.users:
            return None
        return self.users[useruuid].bundle.to_dict()
    
    def get_user(self, user_uuid: str) -> Optional[User]:
        """获取用户对象"""
        return self.users.get(user_uuid)