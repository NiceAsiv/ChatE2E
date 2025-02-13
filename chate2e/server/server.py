from flask import Flask, request, jsonify
from typing import NamedTuple, FrozenSet, Dict, Optional
from base64 import b64encode, b64decode
from flask_cors import CORS
from datetime import datetime
import json
from typing import List
import uuid
import os
from message_manager import Message, MessageManager,SessionManager
from chate2e.crypto.protocol.types import Bundle

app = Flask(__name__)
CORS(app)  # 启用CORS支持

def generate_short_uuid() -> str:
    """生成16位的UUID"""
    return uuid.uuid4().hex[:16]  

class User:
    def __init__(self, username: str, uuid: str):
        self.username = username
        self.uuid = uuid
        self.bundle: Optional[Bundle] = None
        self.used_pre_keys: set = set()
        self.offline_messages: List[Message] = []
        self.is_online: bool = False
    
    def to_dict(self) -> dict:
        return {
            'username': self.username,
            'uuid': self.uuid,
            'bundle': self.bundle.to_dict() if self.bundle else None,
            'is_online': self.is_online
        }
    def set_bundle(self, bundle: Bundle) -> None:
        """设置用户的密钥Bundle"""
        self.bundle = bundle
        self.used_pre_keys.clear()

    def get_bundle_with_unused_prekey(self) -> Optional[dict]:
        """获取包含未使用pre_key的Bundle"""
        if not self.bundle:
            return None

        unused_pre_keys = set(self.bundle.pre_keys) - self.used_pre_keys
        if not unused_pre_keys:
            return None

        selected_pre_key = next(iter(unused_pre_keys))
        self.used_pre_keys.add(selected_pre_key)

        return Bundle(
            identity_key=self.bundle.identity_key,
            signed_pre_key=self.bundle.signed_pre_key,
            signed_pre_key_signature=self.bundle.signed_pre_key_signature,
            pre_keys=frozenset([selected_pre_key])
        ).to_dict()

    def add_offline_message(self, message: Message) -> None:
        """添加离线消息"""
        self.offline_messages.append(message)

    def get_and_clear_offline_messages(self) -> List[dict]:
        """获取并清空离线消息"""
        messages = [msg.to_dict() for msg in self.offline_messages]
        self.offline_messages.clear()
        return messages
            
class ChatServer:
    def __init__(self):
        self.users: Dict[str, User] = {}  # 用户ID -> 用户实例
        self.username_map: Dict[str, str] = {}  # username -> uuid
        self.session_manager = SessionManager()
        self.message_manager = MessageManager()
        self._load_users()

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
        
        # 更新会话活动时间
        self.session_manager.update_session_activity(session_id)
        
        # 保存消息历史
        self.message_manager.add_message(message)
        
        # 如果接收者离线,存储为离线消息
        if not self.online_users.get(receiver_id, False):
            self.message_manager.add_offline_message(message)
            
        return message

        
# 创建全局的ChatServer实例
chat_server = ChatServer()

@app.route('/register', methods=['POST'])
def register():
    """注册新用户并上传其Bundle"""
    data = request.get_json()
    username = data.get('username')
    key_bundle = data.get('key_bundle')
    
    if not all([username, key_bundle]):
        return jsonify({
            'status': 'error', 
            'message': '缺少用户名或密钥Bundle'
        }), 400
        
    user_uuid = chat_server.register_user(username, key_bundle)
    if user_uuid:
        return jsonify({
            'status': 'success',
            'message': '注册成功',
            'uuid': user_uuid
        })
    else:
        return jsonify({
            'status': 'error',
            'message': '注册失败,用户名已存在'
        }), 400

@app.route('/key_bundle/<user_uuid>', methods=['GET'])
def get_key_bundle(user_uuid):
    """获取指定用户的密钥Bundle"""
    user = chat_server.get_user(user_uuid)
    if not user:
        return jsonify({
            'status': 'error',
            'message': '用户不存在'
        }), 404

    bundle = user.get_bundle_with_unused_prekey()
    if bundle:
        return jsonify({
            'status': 'success',
            'key_bundle': bundle
        })
    else:
        return jsonify({
            'status': 'error',
            'message': '无法获取密钥Bundle'
        }), 404
        
@app.route('/key_bundle', methods=['PUT'])
def update_key_bundle():
    """更新用户的密钥Bundle"""
    data = request.get_json()
    user_uuid = data.get('uuid')
    key_bundle = data.get('key_bundle')
    
    if not all([user_uuid, key_bundle]):
        return jsonify({
            'status': 'error', 
            'message': '缺少必要参数'
        }), 400

    user = chat_server.get_user(user_uuid)
    if not user:
        return jsonify({
            'status': 'error',
            'message': '用户不存在'
        }), 404

    try:
        user.set_bundle(Bundle.from_dict(key_bundle))
        chat_server._save_users()
        return jsonify({
            'status': 'success',
            'message': '密钥Bundle更新成功'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': '密钥Bundle更新失败'
        }), 400
        
@app.route('/status/<user_uuid>', methods=['GET'])
def get_user_status(user_uuid):
    """获取用户在线状态"""
    user = chat_server.get_user(user_uuid)
    if not user:
        return jsonify({
            'status': 'error',
            'message': '用户不存在'
        }), 404

    return jsonify({
        'status': 'success',
        'online': user.is_online
    })

@app.route('/status', methods=['PUT'])
def update_user_status():
    """更新用户在线状态"""
    data = request.get_json()
    user_uuid = data.get('uuid')
    online = data.get('online', True)
    
    if not user_uuid:
        return jsonify({
            'status': 'error',
            'message': '缺少UUID'
        }), 400

    user = chat_server.get_user(user_uuid)
    if not user:
        return jsonify({
            'status': 'error',
            'message': '用户不存在'
        }), 404

    user.is_online = online
    chat_server._save_users()
    return jsonify({
        'status': 'success',
        'message': '状态更新成功'
    })
    
@app.route('/session', methods=['POST'])
def create_session():
    """创建新会话"""
    data = request.get_json()
    initiator_id = data.get('initiator_id')
    recipient_id = data.get('recipient_id')
    
    if not all([initiator_id, recipient_id]):
        return jsonify({
            'status': 'error',
            'message': '缺少必要参数'
        }), 400
    
    session_id = chat_server.session_manager.create_session(initiator_id, recipient_id)
    return jsonify({
        'status': 'success',
        'session_id': session_id
    })

@app.route('/session/<user_id>', methods=['GET'])
def get_user_sessions(user_id):
    """获取用户的所有会话"""
    sessions = chat_server.session_manager.get_user_sessions(user_id)
    return jsonify({
        'status': 'success',
        'sessions': sessions
    })

@app.route('/message', methods=['POST'])
def handle_message():
    """处理消息发送"""
    data = request.get_json()
    sender_id = data.get('sender_id')
    receiver_id = data.get('receiver_id')
    session_id = data.get('session_id')
    encrypted_content = data.get('encrypted_content')
    encryption = data.get('encryption')
    
    if not all([sender_id, receiver_id, session_id, encrypted_content]):
        return jsonify({
            'status': 'error',
            'message': '缺少必要参数'
        }), 400
        
    # 验证会话
    session = chat_server.session_manager.get_session(session_id)
    if not session:
        return jsonify({
            'status': 'error',
            'message': '无效的会话ID'
        }), 404
        
    # 处理消息
    message = chat_server.handle_message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        session_id=session_id,
        encrypted_content=encrypted_content,
        encryption=encryption
    )
    
    return jsonify({
        'status': 'success',
        'message_id': message.message_id
    })


@app.route('/messages/offline/<user_id>', methods=['GET'])
def get_offline_messages(user_id):
    """获取用户的离线消息"""
    messages = [
        msg.to_dict() 
        for msg in chat_server.message_manager.get_offline_messages(user_id)
    ]
    return jsonify({
        'status': 'success',
        'messages': messages
    })

@app.route('/messages/session/<session_id>', methods=['GET'])
def get_session_messages(session_id):
    """获取会话的消息历史"""
    messages = [
        msg.to_dict() 
        for msg in chat_server.message_manager.get_session_messages(session_id)
    ]
    return jsonify({
        'status': 'success',
        'messages': messages
    })
    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)