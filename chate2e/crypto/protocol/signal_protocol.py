from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import x25519
from chate2e.crypto.crypto_helper import CryptoHelper
from chate2e.model.message import Message, MessageType, Encryption, X3DHparams
import base64

class SignalProtocol:
    def __init__(self):
        self.crypto_helper = CryptoHelper()

        # 身份密钥对
        self.identity_key = None
        self.identity_key_pub = None
        
        # 预签名密钥对
        self.signed_prekey = None
        self.signed_prekey_pub = None

        # 一次性预密钥集合
        self.one_time_prekeys: Dict[int, Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]] = {}
        
        # 会话密钥
        self.root_key = None
        self.sending_chain_key = None
        self.receiving_chain_key = None
        
        # 会话状态
        self.session_initialized = False
        self.is_initiator = False
        self.session_id = None
        self.user_id = None
        self.peer_id = None
    
    def initialize_identity(self, user_id: str):
        """初始化用户身份"""
        self.user_id = user_id
        self.identity_key = self.crypto.generate_priv_x25519_keypair()
        self.identity_key_pub = self.identity_key.public_key()
        self.generate_signed_prekey()

    def generate_signed_prekey(self) -> None:
        """生成预签名密钥对"""
        self.signed_prekey = self.crypto.generate_priv_x25519_keypair()
        self.signed_prekey_pub = self.signed_prekey.public_key()

    def generate_one_time_prekey(self) -> int:
        """生成一次性预密钥对"""
        key_id = len(self.one_time_prekeys)
        private_key = self.crypto.generate_priv_x25519_keypair()
        public_key = private_key.public_key()
        self.one_time_prekeys[key_id] = (private_key, public_key)
        return key_id
    
    async def initiate_session(self,
                             peer_id: str,
                             recipient_identity_key: x25519.X25519PublicKey,
                             recipient_signed_prekey: x25519.X25519PublicKey,
                             recipient_one_time_prekey: Optional[x25519.X25519PublicKey] = None,
                             is_initiator: bool = True) -> Message:
        """初始化会话"""
        self.is_initiator = is_initiator
        self.peer_id = peer_id
        self.session_id = Message.generate_id()  # 生成新的会话ID

        # 计算共享密钥
        if is_initiator:
            # 生成临时密钥对
            self.ephemeral_key = self.crypto.generate_priv_x25519_keypair()
            self.ephemeral_key_pub = self.ephemeral_key.public_key()
            
            # 计算DH值
            dh1 = self.crypto.ecdh(self.identity_key, recipient_signed_prekey)
            dh2 = self.crypto.ecdh(self.ephemeral_key, recipient_identity_key)
            dh3 = self.crypto.ecdh(self.ephemeral_key, recipient_signed_prekey)
            
            shared_secret = dh1 + dh2 + dh3
            
            if recipient_one_time_prekey:
                dh4 = self.crypto.ecdh(self.ephemeral_key, recipient_one_time_prekey)
                shared_secret += dh4

            # 创建会话初始化消息
            x3dh_params = X3DHparams(
                identity_key_pub=base64.b64encode(
                    self.crypto.export_x25519_public_key(self.identity_key)
                ).decode('utf-8'),
                ephemeral_key_pub=base64.b64encode(
                    self.crypto.export_x25519_public_key(self.ephemeral_key)
                ).decode('utf-8')
            )
        else:
            # 这部分代码将在另一端的session建立时处理
            raise ValueError("非发起方不应调用此方法初始化会话")

        # 派生根密钥和链密钥
        self.root_key = self.crypto.hkdf(shared_secret, 32, info=b"root_key")
        
        # 为发送和接收派生初始链密钥
        self.sending_chain_key = self.crypto.hkdf(shared_secret, 32, 
                                                 salt=self.root_key,
                                                 info=b"sending_chain_key")
        self.receiving_chain_key = self.crypto.hkdf(shared_secret, 32,
                                                   salt=self.root_key,
                                                   info=b"receiving_chain_key")

        # 交换发送和接收密钥（如果是响应方）
        if not is_initiator:
            self.sending_chain_key, self.receiving_chain_key = \
                self.receiving_chain_key, self.sending_chain_key

        self.session_initialized = True

        # 创建初始化消息
        return Message(
            message_id=Message.generate_id(),
            sender_id=self.user_id,
            receiver_id=peer_id,
            session_id=self.session_id,
            message_type=MessageType.INITIATE,
            encrypted_content="",  # 初始化消息不需要加密内容
            X3DHparams=x3dh_params
        )
        
    async def encrypt_message(self, plaintext: str) -> Message:
        """加密消息"""
        if not self.session_initialized:
            raise Exception("Session not initialized")
            
        # 派生消息密钥
        message_key = self.crypto.hkdf(self.sending_chain_key, 32, 
                                     info=b"message_key")
        
        # 生成随机IV
        iv = self.crypto.get_random_bytes(12)
        
        # 使用AES-GCM加密
        ciphertext, tag = self.crypto.encrypt_aes_gcm(message_key, 
                                                     plaintext.encode(), 
                                                     iv)
        
        # 更新发送链密钥
        self.sending_chain_key = self.crypto.hkdf(self.sending_chain_key, 32,
                                                 info=b"next_chain_key")
        
        # 创建加密参数
        encryption = Encryption(
            algorithm="AES-GCM",
            iv=base64.b64encode(iv).decode('utf-8'),
            tag=base64.b64encode(tag).decode('utf-8'),
            is_initiator=self.is_initiator
        )
        
        # 创建加密消息
        return Message(
            message_id=Message.generate_id(),
            sender_id=self.user_id,
            receiver_id=self.peer_id,
            session_id=self.session_id,
            message_type=MessageType.MESSAGE,
            encrypted_content=base64.b64encode(ciphertext).decode('utf-8'),
            encryption=encryption
        )    

    async def decrypt_message(self, message: Message) -> str:
        """解密消息"""
        if not self.session_initialized:
            raise Exception("Session not initialized")
            
        # 检查消息来源和密钥选择
        is_from_initiator = message.encryption.is_initiator
        use_receiving_key = (is_from_initiator and not self.is_initiator) or \
                          (not is_from_initiator and self.is_initiator)
        
        # 选择正确的链密钥
        current_key = self.receiving_chain_key if use_receiving_key else self.sending_chain_key
        
        # 派生消息密钥
        message_key = self.crypto.hkdf(current_key, 32, info=b"message_key")
        
        # 解密消息
        try:
            iv = base64.b64decode(message.encryption.iv)
            tag = base64.b64decode(message.encryption.tag)
            ciphertext = base64.b64decode(message.encrypted_content)
            
            plaintext = self.crypto.decrypt_aes_gcm(
                message_key,
                ciphertext,
                iv,
                tag
            )
            
            # 更新接收链密钥
            if use_receiving_key:
                self.receiving_chain_key = self.crypto.hkdf(current_key, 32,
                                                          info=b"next_chain_key")
            else:
                self.sending_chain_key = self.crypto.hkdf(current_key, 32,
                                                         info=b"next_chain_key")
                
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise Exception(f"Message decryption failed: {str(e)}")