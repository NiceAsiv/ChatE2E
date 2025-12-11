from flask import Flask, request, jsonify
from flask_cors import CORS

from chate2e.model.bundle import Bundle
from chate2e.model.message import Message, MessageType, Encryption
from chate2e.server.chat_server import ChatServer, generate_short_uuid
from chate2e.server.socket_manager import socketio
from chate2e.server.user import User
from chate2e.server.message_manager import MessageManager

app = Flask(__name__)
CORS(app)
socketio.init_app(app)

# 创建全局的ChatServer实例
chat_server = ChatServer()
message_manager = MessageManager()


@socketio.on('connect')
def handle_connect():
    """处理新连接"""
    print(f"新连接: {request.sid}")


@socketio.on('login')
def handle_login(data):
    """处理登录事件"""
    user_id = data.get('user_id')
    if user_id:
        chat_server.add_socket_session(user_id, request.sid)
        return {'status': 'success', 'message': '连接成功'}
    return {'status': 'error', 'message': '登录失败'}

@socketio.on('disconnect')
def handle_disconnect():
    """处理断开连接"""
    print(f"连接断开: {request.sid}")
    chat_server.remove_socket_session(request.sid)


@socketio.on('new_message')
def handle_new_message(message_data):
    """处理新消息"""
    try:
        message = Message.from_dict(message_data)
        chat_server.forward_message(message)
        return {'status': 'success'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/register', methods=['POST'])
def register_user():
    """注册新用户"""
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({
            'status': 'error',
            'message': '缺少用户名'
        }), 400

    useruuid = generate_short_uuid()
    user = User(username, useruuid)
    chat_server.users[useruuid] = user
    chat_server.username_map[username] = useruuid
    chat_server._save_users()

    return jsonify({
        'status': 'success',
        'message': '注册成功',
        'uuid': useruuid
    })


@app.route('/register/bundle', methods=['PUT'])
def upload_initial_bundle():
    """上传用户初始Bundle"""
    data = request.get_json()
    user_uuid = data.get('uuid')
    key_bundle = data.get('key_bundle')

    if not all([user_uuid, key_bundle]):
        return jsonify({
            'status': 'error',
            'message': '缺少UUID或密钥Bundle'
        }), 400

    user = chat_server.get_user(user_uuid)
    if not user:
        return jsonify({
            'status': 'error',
            'message': '用户不存在'
        }), 404

    try:
        user.set_bundle(Bundle.from_dict(key_bundle))
        user.is_online = True
        chat_server._save_users()
        return jsonify({
            'status': 'success',
            'message': '初始Bundle上传成功'
        })

    except Exception as e:
        print(f"上传初始Bundle失败: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Bundle上传失败'
        }), 400

@app.route('/user/<user_uuid>', methods=['GET'])
def get_username_by_uuid(user_uuid: str):  # Changed to match the route parameter
    """通过UUID获取用户名"""
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

    return jsonify({
        'status': 'success',
        'username': user.username
    })

@app.route('/key_bundle/<user_uuid>', methods=['GET'])
def get_key_bundle(user_uuid):
    """获取指定用户的密钥Bundle,并确保返回未使用的一次性预密钥"""
    user = chat_server.get_user(user_uuid)
    if not user:
        return jsonify({
            'status': 'error',
            'message': '用户不存在'
        }), 404

    try:
        bundle = user.get_bundle()
        if bundle:
            return jsonify({
                'status': 'success',
                'key_bundle': bundle.to_dict()
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '用户Bundle不存在'
            }), 404
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取Bundle失败: {str(e)}'
        }), 500


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


@app.route('/handle_message', methods=['POST'])
def handle_message():
    """处理HTTP消息发送请求"""
    try:
        print("\n[Server] ===== 收到handle_message请求 =====")
        data = request.get_json()
        print(f"[Server] 请求数据: {data.get('header', {}).get('message_type')}")
        
        message = Message.from_dict(data)
        print(f"[Server] 解析消息成功")
        print(f"[Server] 消息类型: {message.header.message_type}")
        print(f"[Server] 发送者: {message.header.sender_id}")
        print(f"[Server] 接收者: {message.header.receiver_id}")
        print(f"[Server] 会话ID: {message.header.session_id}")
        
        # 对于INITIATE消息，服务器需要先创建或验证会话
        if message.header.message_type == MessageType.INITIATE:
            # 确保会话存在
            existing_session_id = chat_server.get_or_create_session(
                message.header.sender_id,
                message.header.receiver_id
            )
            print(f"[Server] INITIATE消息的会话ID: {existing_session_id}")
            # 如果客户端发送的session_id与服务器的不同，记录警告
            if existing_session_id != message.header.session_id:
                print(f"[Server] ⚠ 警告: 客户端session_id ({message.header.session_id}) 与服务器 ({existing_session_id}) 不同")
        else:
            # 验证会话（对于非INITIATE消息）
            if not chat_server.validate_session(message.header.session_id, message.header.sender_id):
                print(f"[Server] ✗ 会话验证失败")
                return jsonify({
                    'status': 'error',
                    'message': '会话验证失败'
                }), 403
        
        result = chat_server.forward_message(message)
        print(f"[Server] forward_message返回: {result}")
        
        return jsonify({
            'status': 'success',
            'message_id': message.header.message_id,
            'delivered': result
        })
    except Exception as e:
        print(f"[Server] ✗ 处理消息异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'消息处理失败: {str(e)}'
        }), 500


@app.route('/messages/offline/<user_id>', methods=['GET'])
def get_offline_messages(user_id):
    """获取并清空用户的离线消息"""
    try:
        messages = message_manager.get_offline_messages(user_id)
        return jsonify({
            'status': 'success',
            'messages': [msg.to_dict() for msg in messages]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取离线消息失败: {str(e)}'
        }), 500


@app.route('/session/get', methods=['POST'])
def get_session():
    """获取或创建两个用户之间的会话ID
    
    请求体:
    {
        "user1_id": "用户1的ID",
        "user2_id": "用户2的ID"
    }
    
    返回:
    {
        "status": "success",
        "session_id": "会话ID",
        "is_new": true/false
    }
    """
    try:
        data = request.get_json()
        user1_id = data.get('user1_id')
        user2_id = data.get('user2_id')
        
        if not user1_id or not user2_id:
            return jsonify({
                'status': 'error',
                'message': '缺少用户ID'
            }), 400
        
        # 验证用户是否存在
        if user1_id not in chat_server.users or user2_id not in chat_server.users:
            return jsonify({
                'status': 'error',
                'message': '用户不存在'
            }), 404
        
        # 检查是否已存在会话
        is_new = True
        if user1_id in chat_server.user_sessions:
            if user2_id in chat_server.user_sessions[user1_id]:
                is_new = False
        
        # 获取或创建会话
        session_id = chat_server.get_or_create_session(user1_id, user2_id)
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'is_new': is_new
        })
        
    except Exception as e:
        print(f"[Server] 获取会话失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'获取会话失败: {str(e)}'
        }), 500


@app.route('/friend/add', methods=['POST'])
def add_friend():
    """添加好友并通知对方"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')  # 发起请求的用户
        friend_id = data.get('friend_id')  # 要添加的好友
        username = data.get('username')  # 发起请求的用户名
        
        if not all([user_id, friend_id, username]):
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
        
        # 通过SocketIO通知对方用户
        # 查找对方的socket连接
        friend_socket_id = None
        for socket_id, uid in chat_server.socket_sessions.items():
            if uid == friend_id:
                friend_socket_id = socket_id
                break
        
        if friend_socket_id:
            # 对方在线，发送实时通知
            socketio.emit('friend_request', {
                'user_id': user_id,
                'username': username
            }, room=friend_socket_id)
        
        return jsonify({
            'status': 'success',
            'message': '好友添加请求已发送'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'添加好友失败: {str(e)}'
        }), 500


@app.route('/friend/remove', methods=['POST'])
def remove_friend():
    """删除好友并通知对方"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')  # 发起请求的用户
        friend_id = data.get('friend_id')  # 要删除的好友
        
        if not all([user_id, friend_id]):
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
        
        # 通过SocketIO通知对方用户
        friend_socket_id = None
        for socket_id, uid in chat_server.socket_sessions.items():
            if uid == friend_id:
                friend_socket_id = socket_id
                break
        
        if friend_socket_id:
            # 对方在线，发送删除通知
            socketio.emit('friend_removed', {
                'user_id': user_id
            }, room=friend_socket_id)
        
        return jsonify({
            'status': 'success',
            'message': '好友已删除'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'删除好友失败: {str(e)}'
        }), 500


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)