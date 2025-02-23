from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Dict, Optional
from flask_cors import CORS
import json
from typing import List
import uuid
import os
from message_manager import MessageManager
from chate2e.model.bundle import Bundle
from chate2e.model.message import Message, MessageType, Encryption
from chate2e.server.user import User

app = Flask(__name__)
CORS(app)  # 启用CORS支持
socketio = SocketIO(app, cors_allowed_origins="*")

def generate_short_uuid() -> str:
    """生成16位的UUID"""
    return uuid.uuid4().hex[:16]  
            
class ChatServer:
    def __init__(self):
        self.users: Dict[str, User] = {}  # 用户ID -> 用户实例
        self.username_map: Dict[str, str] = {}  # username -> uuid
        self.socket_sessions: Dict[str, str] = {}  # user_id -> socket_id
        self.message_manager = MessageManager()
        self._load_users()
     
    def add_socket_session(self, user_id: str, socket_id: str) -> None:
        """添加Socket会话"""
        self.socket_sessions[user_id] = socket_id
        user = self.users.get(user_id)
        if user and user.offline_messages:
            for message in user.offline_messages:
                emit('message', message.to_dict())
            user.offline_messages.clear()
            user.is_online = True
            self._save_users()
        
    def remove_socket_session(self, socket_id: str) -> None:
        """移除Socket会话"""
        for user_id, sid in list(self.socket_sessions.items()):
            if sid == socket_id:
                del self.socket_sessions[user_id]
                user = self.get_user(user_id)
                if user:
                    user.is_online = False
                    self._save_users()
                break

    def forward_message(self, message: Message) -> bool:
        """转发消息到目标用户"""
        receiver_id = message.header.receiver_id
        # 检查接收者是否在线
        if receiver_id in self.socket_sessions:
            socket_id = self.socket_sessions[receiver_id]
            try:
                # 通过socket发送消息
                socketio.emit('new_message', message.to_dict(), room=socket_id)
                return True
            except Exception as e:
                print(f"消息转发失败: {e}")
                return False
        else:
            # 接收者离线，存储为离线消息
            receiver = self.users.get(receiver_id)
            if receiver:
                receiver.offline_messages.append(message)
                self._save_users()
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
    
    def handle_message(self, sender_id: str, receiver_id: str, 
                      session_id: str, encrypted_content: str,
                      encryption: Optional[Dict] = None) -> Message:
        """处理新消息"""
        # 创建消息对象
        message = Message(
            message_id=Message.generate_id(),
            session_id=session_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            encrypted_content=encrypted_content,
            encryption=encryption
        )
        
        # 保存消息历史
        self.message_manager.add_message(message)
        
        # 如果接收者离线,存储为离线消息
        if not self.online_users.get(receiver_id, False):
            self.message_manager.add_offline_message(message)
            
        return message