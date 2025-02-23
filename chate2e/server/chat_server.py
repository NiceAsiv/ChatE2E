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
        self._load_users()

    def forward_message(self, message: Message) -> bool:
        """广播消息给所有连接的客户端"""
        try:
            socketio.emit('message', message.to_dict())
            return True
        except Exception as e:
            print(f"广播消息失败: {e}")
            return False
    
    def _load_users(self) -> None:
        """加载用户信息"""
        # 从本地或者数据库加载用户信息
        try:
            if os.path.exists('data/users.json'):
                with open('data/users.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data['users']:
                        user = User(user_data['username'], user_data['uuid'])
                        if user_data.get('bundle'):
                            user.bundle = Bundle.from_dict(user_data['bundle'])
                        self.users[user.uuid] = user
                        self.username_map[user.username] = user.uuid
        except Exception as e:
            print(f"加载用户数据失败: {e}")
    
    def _save_users(self) -> None:
        """保存用户信息"""
        try:
            data = {
                'users': [user.to_dict() for user in self.users.values()]
            }
            with open('data/users.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
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