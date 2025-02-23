from flask import Flask, request, jsonify
from flask_cors import CORS

from chate2e.model.bundle import Bundle
from chate2e.model.message import Message, MessageType, Encryption
from chate2e.server.chat_server import ChatServer, generate_short_uuid
from chate2e.server.socket_manager import socketio
from chate2e.server.user import User
app = Flask(__name__)
CORS(app)
socketio.init_app(app)

# 创建全局的ChatServer实例
chat_server = ChatServer()


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


@app.route('/handle_message', methods=['POST'])
def handle_message():
    """处理HTTP消息发送请求"""
    try:
        data = request.get_json()
        message = Message.from_dict(data)
        chat_server.forward_message(message)
        
        return jsonify({
            'status': 'success',
            'message_id': message.header.message_id,
            'delivered': True
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'消息处理失败: {str(e)}'
        }), 500


@app.route('/messages/offline/<user_id>', methods=['GET'])
def get_offline_messages(user_id):
    """获取并清空用户的离线消息"""
    try:
        messages = chat_server.message_manager.get_offline_messages(user_id)
        return jsonify({
            'status': 'success',
            'messages': [msg.to_dict() for msg in messages]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取离线消息失败: {str(e)}'
        }), 500



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)