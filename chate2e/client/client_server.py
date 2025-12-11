import time
from typing import Optional, Dict, Callable, List, Tuple

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
        self.friend_update_handlers: List[Callable] = []  # 好友更新回调列表

        # 注册好友请求事件
        @self.sio.on('friend_request')
        def on_friend_request(data):
            try:
                print(f"收到好友请求: {data}")
                from chate2e.client.models import Friend, UserStatus
                # 自动添加好友
                new_friend = Friend(
                    user_id=data['user_id'],
                    username=data['username'],
                    avatar_path='',
                    status=UserStatus.ONLINE
                )
                self.data_manager.add_friend(new_friend)
                print(f"已自动添加好友: {data['username']}")
                
                # 触发好友列表刷新回调
                for handler in getattr(self, 'friend_update_handlers', []):
                    handler()
                    
            except Exception as e:
                print(f"处理好友请求失败: {e}")
        
        # 注册好友删除事件
        @self.sio.on('friend_removed')
        def on_friend_removed(data):
            try:
                print(f"收到好友删除通知: {data}")
                # 删除好友
                removed_user_id = data['user_id']
                self.data_manager.user.remove_friend(removed_user_id)
                self.data_manager.save_user_profile()
                print(f"已删除好友: {removed_user_id}")
                
                # 触发好友列表刷新回调
                for handler in getattr(self, 'friend_update_handlers', []):
                    handler()
                    
            except Exception as e:
                print(f"处理好友删除失败: {e}")
        
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
                    # 初始化会话 - 使用发送方的session_id
                    session = self.data_manager.get_or_create_session_with_id(
                        message.header.session_id,
                        message.header.sender_id
                    )
                    print(f"[Client] 接收到会话初始化请求，session_id: {message.header.session_id}")
                    
                    self.init_session_bob(message)
                    self.protocol.session_initialized = True
                    #保存消息
                    self.data_manager.add_message(message.header.session_id, message)
                    return

                if message.header.message_type == MessageType.ACK_INITIATE:
                    self.protocol.session_initialized = True
                    return
                
                # 处理普通消息
                if message.header.message_type == MessageType.MESSAGE:
                    if not self.protocol.session_initialized:
                        print(f"[Client] ✗ 会话未初始化，无法解密")
                        return
                    
                    # 通知所有注册的消息处理器
                    for handler in self.message_handlers:
                        handler(message)

            except Exception as e:
                print(f"[Client] ✗ 消息处理失败: {e}")
                import traceback
                traceback.print_exc()

    def register_message_handler(self, handler: Callable[[Message], None]):
        """注册消息处理器

        Args:
            handler: 处理消息的回调函数，接收 (message: Message) 作为参数
        """
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)
    
    def register_friend_update_handler(self, handler: Callable[[], None]):
        """注册好友更新处理器
        
        Args:
            handler: 处理好友列表更新的回调函数
        """
        if handler not in self.friend_update_handlers:
            self.friend_update_handlers.append(handler)

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
                recipient_one_time_prekey=None,  # 这个参数只在Alice作为发起方时使用
                recipient_ephemeral_key=ephemeral_key,
                own_one_time_prekey=one_time_prekey,  # Bob自己的one_time_prekey
                is_initiator=False
            )
            
            # 标记会话已初始化并保存session_id映射
            self.sessions[message.header.sender_id] = True
            self.sessions[f"{message.header.sender_id}_session_id"] = message.header.session_id
            
            # 发送确认消息（直接发送HTTP请求，避免递归）
            print(f"[Client] 发送ACK_INITIATE消息，session_id: {message.header.session_id}")
            message_dict = ack_message.to_dict()
            response = requests.post(
                f"{self.server_url}/handle_message",
                json=message_dict
            )
            
            if response.status_code != 200:
                print(f"发送ACK消息失败: {response.status_code}")
                return False
            
            #保存消息
            self.data_manager.add_message(message.header.session_id, ack_message)
            
            print(f"✓ Bob端会话初始化成功: {message.header.sender_id}, session_id: {message.header.session_id}")
            
            return True
        
        except Exception as e:
            print(f"会话初始化失败: {e}")
            return

    def init_session_sync(self, peer_id: str , session_id: str = None) -> Tuple[bool, str]:
        """同步初始化与peer的通信会话
        
        Args:
            peer_id: 对方用户ID
            session_id: 可选的会话ID，如果不提供则从服务器获取
            
        Returns:
            (success: bool, session_id: str): 是否成功和会话ID
        """
        if peer_id in self.sessions:
            print(f"会话已存在，跳过初始化: {peer_id}")
            # 返回现有的session_id
            existing_session_id = self.sessions.get(f"{peer_id}_session_id")
            if existing_session_id:
                return True, existing_session_id
            else:
                # 如果没有保存session_id，需要重新初始化
                print(f"[Client] 警告: 会话存在但没有session_id，重新初始化")
                del self.sessions[peer_id]
        
        try:
            # 1. 从服务器获取或创建session_id
            if not session_id:
                print(f"[Client] 从服务器获取会话ID")
                response = requests.post(
                    f"{self.server_url}/session/get",
                    json={
                        'user1_id': self.user_id,
                        'user2_id': peer_id
                    },
                    timeout=5
                )
                
                if response.status_code != 200:
                    print(f"获取会话ID失败: {response.status_code}")
                    return False, None
                
                result = response.json()
                session_id = result['session_id']
                is_new = result['is_new']
                print(f"[Client] 获得会话ID: {session_id} (新会话: {is_new})")
            
            print(f"[Client] 正在初始化与 {peer_id} 的会话，session_id: {session_id}")
            
            # 2. 获取对方的Bundle
            response = requests.get(f"{self.server_url}/key_bundle/{peer_id}")
            if response.status_code != 200:
                print(f"获取对方Bundle失败: {response.status_code}")
                return False, None

            bundle_data = response.json()['key_bundle']
            peer_bundle = Bundle.from_dict(bundle_data)

            # 3. 将bytes转换为X25519PublicKey对象
            identity_key = X25519PublicKey.from_public_bytes(peer_bundle.identity_key_pub)
            signed_prekey = X25519PublicKey.from_public_bytes(peer_bundle.signed_pre_key_pub)
            one_time_prekey = X25519PublicKey.from_public_bytes(next(iter(peer_bundle.one_time_pre_keys_pub)))

            # 4. 初始化Signal会话
            x3dh_message = self.protocol.initiate_session(
                peer_id=peer_id,
                session_id=session_id,
                recipient_identity_key=identity_key,
                recipient_signed_prekey=signed_prekey,
                recipient_one_time_prekey=one_time_prekey,
                is_initiator=True
            )

            # 5. 发送X3DH消息（直接发送，不检查会话状态，避免递归）
            print(f"[Client] 发送会话初始化消息到服务器")
            message_dict = x3dh_message.to_dict()
            response = requests.post(
                f"{self.server_url}/handle_message",
                json=message_dict
            )
            
            if response.status_code != 200:
                print(f"发送初始化消息失败: {response.status_code}")
                return False, None

            # 6. 保存消息
            self.data_manager.add_message(session_id, x3dh_message)
            
            # 7. 等待ACK_INITIATE消息的确认
            timeout = 20  # 20秒超时
            start_time = time.time()
            while not self.protocol.session_initialized:
                if time.time() - start_time > timeout:
                    print("等待会话初始化确认超时")
                    return False, None
                time.sleep(0.1)  # 短暂睡眠避免CPU过载

            # 8. 标记会话已初始化
            self.sessions[peer_id] = True
            self.sessions[f"{peer_id}_session_id"] = session_id  # 保存session_id映射
            print(f"✓ 会话初始化成功: {peer_id}, session_id: {session_id}")

            return True, session_id
            
        except Exception as e:
            print(f"会话初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False, None

    def send_message_sync(self, peer_id: str, message: Message) -> bool:
        """同步发送加密消息"""
        # 注意：不在这里检查会话状态，由调用方负责初始化会话
        try:
            print(f"[Client] 发送消息到服务器: {self.server_url}/handle_message")
            print(f"[Client] 消息类型: {message.header.message_type}")
            print(f"[Client] 发送者: {message.header.sender_id}")
            print(f"[Client] 接收者: {message.header.receiver_id}")
            print(f"[DEBUG] 发送前encrypted_content类型: {type(message.encrypted_content)}")
            print(f"[DEBUG] 发送前encrypted_content长度: {len(message.encrypted_content) if hasattr(message.encrypted_content, '__len__') else 'N/A'}")
            
            message_dict = message.to_dict()
            print(f"[DEBUG] to_dict后encrypted_content: {message_dict['encrypted_content'][:50]}...")
            
            # 发送到服务器
            response = requests.post(
                f"{self.server_url}/handle_message",
                json=message_dict
            )

            print(f"[Client] 服务器响应: {response.status_code}")
            if response.status_code == 200:
                print(f"[Client] 响应内容: {response.json()}")
            
            return response.status_code == 200

        except Exception as e:
            print(f"发送消息失败: {e}")
            import traceback
            traceback.print_exc()
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
    
    def add_friend_sync(self, friend_id: str) -> bool:
        """同步添加好友并通知对方
        
        Args:
            friend_id: 要添加的好友ID
            
        Returns:
            bool: 添加成功返回True，失败返回False
        """
        try:
            response = requests.post(
                f"{self.server_url}/friend/add",
                json={
                    'user_id': self.user_id,
                    'friend_id': friend_id,
                    'username': self.username
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"好友添加请求已发送到 {friend_id}")
                    return True
            
            print(f"发送好友请求失败: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"发送好友请求失败: {str(e)}")
            return False
    
    def remove_friend_sync(self, friend_id: str) -> bool:
        """同步删除好友并通知对方
        
        Args:
            friend_id: 要删除的好友ID
            
        Returns:
            bool: 删除成功返回True，失败返回False
        """
        try:
            response = requests.post(
                f"{self.server_url}/friend/remove",
                json={
                    'user_id': self.user_id,
                    'friend_id': friend_id
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    print(f"已删除好友: {friend_id}")
                    return True
            
            print(f"删除好友失败: {response.status_code}")
            return False
            
        except Exception as e:
            print(f"删除好友失败: {str(e)}")
            return False

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

