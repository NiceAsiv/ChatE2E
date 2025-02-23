import time
from typing import Optional, Dict, Callable, List

import requests
import socketio
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey

from chate2e.client.models import DataManager
from chate2e.crypto.protocol.signal_protocol import SignalProtocol
from chate2e.model.bundle import Bundle
from chate2e.model.message import Message, MessageType


class ChatClient:
    def __init__(self, server_url: str, data_manager: DataManager):
        self.server_url = server_url
        self.sio = socketio.Client()  # 使用同步版本的 socketio 客户端
        self.protocol = SignalProtocol()
        self.user_id: Optional[str] = None
        self.username: Optional[str] = None
        self.data_manager = data_manager
        self.sessions: Dict[str, bool] = {}
        self.message_handlers: List[Callable] = []
        
        @self.sio.on('message')
        def on_message(data):  # 移除 async
            message = Message.from_dict(data)
            try:
                # 同步解密消息
                decrypted_text = self.protocol.decrypt_message(message)
                for handler in self.message_handlers:
                    handler(message.header.sender_id, decrypted_text)
            except Exception as e:
                print(f"消息处理失败: {e}")

        # 注册消息处理事件
        @self.sio.on('new_message')
        def on_new_message(data):
            try:
                # 解析接收到的消息
                message = Message.from_dict(data)


                # 确保消息是发给自己的
                if message.header.receiver_id != self.user_id:
                    return

                if message.header.message_type == MessageType.INITIATE:
                    # 初始化会话
                    self.init_session_bob(message)
                    self.protocol.session_initialized = True
                    #保存消息
                    self.data_manager.add_message(message.header.session_id,message)
                    return

                if message.header.message_type == MessageType.ACK_INITIATE:
                    self.protocol.session_initialized = True
                # # 初始化会话（如果需要）
                # if message.header.sender_id not in self.sessions:
                #     self.init_session_sync(message.header.sender_id)

                # 通知所有注册的消息处理器
                for handler in self.message_handlers:
                    handler(message)

            except Exception as e:
                print(f"消息处理失败: {e}")

    def register_message_handler(self, handler: Callable[[str, str], None]):
        """注册消息处理器

        Args:
            handler: 处理消息的回调函数，接收 (sender_id: str, message: str) 作为参数
        """
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)

    def register_sync(self, username: str) -> bool:
        """同步注册新用户"""
        try:
            # 注册用户
            response = requests.post(f"{self.server_url}/register", 
                json={'username': username},
                timeout=5)  # 添加超时时间
            if response.status_code != 200:
                print(f"注册失败: 服务器返回状态码 {response.status_code}")
                return False
            
            result = response.json()
            self.user_id = result.get('uuid')
            if not self.user_id:
                print("注册失败: 服务器没有返回用户ID")
                return False
                
            self.username = username
            
            # 初始化Signal协议
            self.protocol.initialize_identity(self.user_id)
            
            # 上传初始Bundle
            bundle = self.protocol.create_bundle()
            response = requests.put(
                f"{self.server_url}/register/bundle",
                json={
                    'uuid': self.user_id,
                    'key_bundle': bundle.to_dict()
                },
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"Bundle上传失败: 服务器返回状态码 {response.status_code}")
                return False
                
            return True
            
        except requests.exceptions.ConnectionError as e:
            print(f"连接服务器失败: 请确保服务器已启动且地址正确 ({self.server_url})")
            return False
        except requests.exceptions.Timeout:
            print("连接服务器超时")
            return False
        except Exception as e:
            print(f"注册失败: {str(e)}")
            return False

    def connect_sync(self) -> bool:
        """同步连接到WebSocket服务器"""
        try:
            self.sio.connect(
                self.server_url,
                wait_timeout=5,
                wait=True,
                transports=['websocket', 'polling']
            )
            if self.user_id:
                self.sio.emit('login', {'user_id': self.user_id})
                return True
            return False
        except Exception as e:
            print(f"连接WebSocket服务器失败: {e}")
            raise ConnectionError(f"WebSocket连接失败: {str(e)}")

    def init_session_bob(self, message: Message):
        """Bob端初始化会话"""
        try:
            x3dh_params = message.X3DHparams
            identity_key = X25519PublicKey.from_public_bytes(x3dh_params.identity_key_pub)
            signed_prekey = X25519PublicKey.from_public_bytes(x3dh_params.signed_pre_key_pub)
            one_time_prekey = X25519PublicKey.from_public_bytes(x3dh_params.one_time_pre_keys_pub)
            ephemeral_key = X25519PublicKey.from_public_bytes(x3dh_params.ephemeral_key_pub)

            # 初始化Signal会话
            ack_message = self.protocol.initiate_session(
                peer_id=message.header.sender_id,
                session_id=message.header.session_id,
                recipient_identity_key=identity_key,
                recipient_signed_prekey=signed_prekey,
                recipient_one_time_prekey=one_time_prekey,
                recipient_ephemeral_key=ephemeral_key,
                is_initiator=False
            )
            self.sessions[message.header.sender_id] = True
            #发送确认消息
            self.send_message_sync(message.header.sender_id, ack_message)
            #保存消息
            self.data_manager.add_message(message.header.session_id,ack_message)
            
            return True
        
        except Exception as e:
            print(f"会话初始化失败: {e}")
            return

    def init_session_sync(self, peer_id: str , session_id: str) -> bool:
        """同步初始化与peer的通信会话"""
        if peer_id in self.sessions:
            return True
        try:
            print(f"正在初始化与 {peer_id} 的会话")
            # 获取对方的Bundle
            response = requests.get(f"{self.server_url}/key_bundle/{peer_id}")
            if response.status_code != 200:
                return False

            bundle_data = response.json()['key_bundle']
            peer_bundle = Bundle.from_dict(bundle_data)

            # 将bytes转换为X25519PublicKey对象
            identity_key = X25519PublicKey.from_public_bytes(peer_bundle.identity_key_pub)
            signed_prekey = X25519PublicKey.from_public_bytes(peer_bundle.signed_pre_key_pub)
            one_time_prekey = X25519PublicKey.from_public_bytes(next(iter(peer_bundle.one_time_pre_keys_pub)))

            # 初始化Signal会话
            x3dh_message = self.protocol.initiate_session(
                peer_id=peer_id,
                session_id= session_id,
                recipient_identity_key=identity_key,
                recipient_signed_prekey=signed_prekey,
                recipient_one_time_prekey=one_time_prekey,
                is_initiator=True
            )

            self.sessions[peer_id] = True

            # 发送X3DH消息
            self.send_message_sync(peer_id, x3dh_message)

            #保存消息
            self.data_manager.add_message(session_id,x3dh_message)
            # 等待ACK_INITIATE消息的确认
            timeout = 20  # 10秒超时
            start_time = time.time()
            while not self.protocol.session_initialized:
                if time.time() - start_time > timeout:
                    print("等待会话初始化确认超时")
                    return False
                time.sleep(0.1)  # 短暂睡眠避免CPU过载

            self.sessions[peer_id] = True

            return True
            
        except Exception as e:
            print(f"会话初始化失败: {e}")
            return False

    def send_message_sync(self, peer_id: str, message: Message) -> bool:
        """同步发送加密消息"""
        if not self.sessions.get(peer_id):
            if not self.init_session_sync(peer_id):
                return False
        try:
            # 发送到服务器
            response = requests.post(
                f"{self.server_url}/handle_message",
                json=message.to_dict()
            )

            return response.status_code == 200

        except Exception as e:
            print(f"发送消息失败: {e}")
            return False

    def disconnect_sync(self):
        """同步断开连接"""
        self.sio.disconnect()

    def get_user_bundle(self, user_id: str) -> Optional[Bundle]:
        """
        获取指定用户的密钥Bundle

        Args:
            user_id: 目标用户ID

        Returns:
            Bundle: 用户的密钥Bundle，如果获取失败则返回None
        """
        try:
            # 发送GET请求获取用户Bundle
            response = requests.get(
                f"{self.server_url}/key_bundle/{user_id}",
                timeout=5
            )

            # 检查响应状态码
            if response.status_code != 200:
                print(f"获取Bundle失败: 服务器返回状态码 {response.status_code}")
                return None

            # 解析响应数据
            result = response.json()
            if result.get('status') != 'success':
                print(f"获取Bundle失败: {result.get('message')}")
                return None

            # 将字典转换为Bundle对象
            bundle = Bundle.from_dict(result['key_bundle'])
            return bundle

        except requests.exceptions.ConnectionError:
            print(f"连接服务器失败: {self.server_url}")
            return None
        except requests.exceptions.Timeout:
            print("请求超时")
            return None
        except Exception as e:
            print(f"获取Bundle失败: {str(e)}")
            return None

    def get_user_name(self, user_id):
        """获取用户昵称"""
        try:
            response = requests.get(
                f"{self.server_url}/user/{user_id}",
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('username')
        except Exception as e:
            print(f"获取用户昵称失败: {e}")
        return None

