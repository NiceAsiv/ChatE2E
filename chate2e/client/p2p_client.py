import socket
import threading
from typing import Optional, Dict, Callable, List
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
from chate2e.crypto.protocol.signal_protocol import SignalProtocol
from chate2e.model.message import Message
from chate2e.model.message import MessageType
from chate2e.model.message import Encryption

class P2PClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.protocol = SignalProtocol()
        self.peer_address = None
        self.user_id = None
        self.username = None
        self.data_manager = None
        self.message_handlers: List[Callable] = []
        
        # 绑定本地端口
        self.socket.bind((host, port))
        
        # 启动接收消息的线程
        self.receive_thread = threading.Thread(target=self._receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def _receive_messages(self):
        """接收消息的循环"""
        while True:
            try:
                data, addr = self.socket.recvfrom(4096)
                message = Message.from_bytes(data)
                
                # 处理接收到的消息
                if message.header.message_type == MessageType.INITIATE:
                    self.handle_init_session(message, addr)
                elif message.header.message_type == MessageType.ACK_INITIATE:
                    self.protocol.handle_ack_message(message)
                else:
                    decrypted = self.protocol.decrypt_message(message)
                    for handler in self.message_handlers:
                        handler(decrypted)
                        
            except Exception as e:
                print(f"接收消息出错: {e}")

    def init_session(self, peer_id: str, peer_host: str, peer_port: int) -> bool:
        """初始化与对等节点的会话"""
        try:
            self.peer_address = (peer_host, peer_port)
            self.protocol.peer_id = peer_id
            
            # 创建并发送初始化消息
            init_message = self.protocol.create_initial_message(
                self.user_id,
                peer_id,
                self.protocol.create_bundle()
            )
            
            # 发送初始化消息
            self.send_message(init_message)
            return True
            
        except Exception as e:
            print(f"会话初始化失败: {e}")
            return False

    def handle_init_session(self, message: Message, addr):
        """处理收到的会话初始化消息"""
        try:
            # 保存对方地址
            self.peer_address = addr
            
            # 从消息中提取对方的密钥Bundle
            peer_bundle = Bundle.from_dict(message.bundle_data)
            
            # 创建响应消息
            response = self.protocol.handle_initial_message(
                message.header.sender_id,
                peer_bundle,
                self.protocol.create_bundle()
            )
            
            # 发送响应
            self.send_message(response)
            
        except Exception as e:
            print(f"处理初始化消息失败: {e}")

    def connect_to_peer(self, peer_host: str, peer_port: int) -> bool:
        """连接到对等节点"""
        try:
            self.peer_address = (peer_host, peer_port)
            # 初始化Signal会话
            init_message = self.protocol.create_initial_message()
            self.send_message(init_message)
            return True
        except Exception as e:
            print(f"连接对等节点失败: {e}")
            return False

    def send_message(self, message: Message) -> bool:
        """发送消息到对等节点"""
        try:
            if not self.peer_address:
                raise Exception("未连接到对等节点")
            
            # 序列化消息
            data = message.to_bytes()
            self.socket.sendto(data, self.peer_address)
            return True
        except Exception as e:
            print(f"发送消息失败: {e}")
            return False

    def register_message_handler(self, handler: Callable[[Message], None]):
        """注册消息处理器"""
        if handler not in self.message_handlers:
            self.message_handlers.append(handler)

    def _handle_initiate_message(self, message: Message, addr):
        """处理初始化消息"""
        try:
            self.peer_address = addr
            ack_message = self.protocol.handle_initial_message(message)
            self.send_message(ack_message)
        except Exception as e:
            print(f"处理初始化消息失败: {e}")

    def _handle_ack_message(self, message: Message):
        """处理确认消息"""
        try:
            self.protocol.handle_ack_message(message)
            print("Signal会话建立成功")
        except Exception as e:
            print(f"处理确认消息失败: {e}")

    def _handle_regular_message(self, message: Message):
        """处理常规消息"""
        try:
            decrypted_text = self.protocol.decrypt_message(message)
            for handler in self.message_handlers:
                handler(decrypted_text)
        except Exception as e:
            print(f"处理消息失败: {e}")

    def close(self):
        """关闭连接"""
        self.socket.close()