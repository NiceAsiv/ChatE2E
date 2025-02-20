from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import os
import json
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
import base64

@dataclass
class EncryptedMessage:
    ciphertext: bytes
    header: Dict
    
class SignalProtocol:
    def __init__(self):
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
        
    def generate_identity_key(self) -> None:
        """生成身份密钥对"""
        self.identity_key = x25519.X25519PrivateKey.generate()
        self.identity_key_pub = self.identity_key.public_key()
    
    def generate_signed_prekey(self) -> None:
        """生成预签名密钥对"""
        self.signed_prekey = x25519.X25519PrivateKey.generate()
        self.signed_prekey_pub = self.signed_prekey.public_key()
    
    def generate_one_time_prekey(self) -> int:
        """生成一次性预密钥对"""
        key_id = len(self.one_time_prekeys)
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        self.one_time_prekeys[key_id] = (private_key, public_key)
        return key_id

    async def initiate_session(self, 
                               recipient_identity_key: x25519.X25519PublicKey,
                               recipient_signed_prekey: x25519.X25519PublicKey,
                               recipient_ephemeral_key: Optional[x25519.X25519PublicKey] = None,
                               recipient_one_time_prekey: Optional[x25519.X25519PublicKey] = None,
                               own_one_time_prekey: Optional[x25519.X25519PublicKey] = None,
                               is_initiator: bool = True) -> bytes:
        """初始化会话（X3DH）"""
        print(f"\n[初始化] 开始会话初始化 (是否为发起方: {is_initiator})")
        self.is_initiator = is_initiator
        
        if is_initiator:
            # 发起方生成临时密钥对
            self.ephemeral_key = x25519.X25519PrivateKey.generate()
            self.ephemeral_key_pub = self.ephemeral_key.public_key()
            
            # 计算 DH
            dh1 = self.identity_key.exchange(recipient_signed_prekey)
            dh2 = self.ephemeral_key.exchange(recipient_identity_key)
            dh3 = self.ephemeral_key.exchange(recipient_signed_prekey)
            
            shared_secret = dh1 + dh2 + dh3
            print(f"[初始化] 发起方生成共享密钥: {shared_secret.hex()[:32]}...")
            
            if recipient_one_time_prekey:
                dh4 = self.ephemeral_key.exchange(recipient_one_time_prekey)
                shared_secret += dh4
        else:
            # 响应方必须传入发起方的临时公钥
            if not recipient_ephemeral_key:
                raise ValueError("响应方初始化时必须提供发起方的临时公钥")
                
            # 计算 DH
            dh1 = self.signed_prekey.exchange(recipient_identity_key)
            dh2 = self.identity_key.exchange(recipient_ephemeral_key)
            dh3 = self.signed_prekey.exchange(recipient_ephemeral_key)
            
            shared_secret = dh1 + dh2 + dh3
            print(f"[初始化] 响应方生成共享密钥: {shared_secret.hex()[:32]}...")
            
            if own_one_time_prekey:
                # 使用响应方自己保存的对应私钥计算 DH4
                for key_id, (priv, pub) in self.one_time_prekeys.items():
                    # 比较公钥原始字节
                    if pub.public_bytes(encoding=serialization.Encoding.Raw,
                                        format=serialization.PublicFormat.Raw) == \
                       own_one_time_prekey.public_bytes(encoding=serialization.Encoding.Raw,
                                                       format=serialization.PublicFormat.Raw):
                        dh4 = priv.exchange(recipient_ephemeral_key)
                        shared_secret += dh4
                        # 可选择使用后删除已使用的一次性预密钥
                        del self.one_time_prekeys[key_id]
                        break
        
        # 生成根密钥（双方基于相同共享密钥应生成相同根密钥）
        self.root_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"root_key"
        ).derive(shared_secret)
        print(f"[初始化] 生成的根密钥: {self.root_key.hex()}")
        
        # 派生初始链密钥
        initial_sending_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.root_key,
            info=b"sending_chain_key"
        ).derive(shared_secret)
        
        initial_receiving_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.root_key,
            info=b"receiving_chain_key"
        ).derive(shared_secret)
        
        # 根据角色分配链密钥
        if is_initiator:
            self.sending_chain_key = initial_sending_key
            self.receiving_chain_key = initial_receiving_key
        else:
            self.sending_chain_key = initial_receiving_key
            self.receiving_chain_key = initial_sending_key
            
        print(f"[初始化] 设置后的发送链密钥: {self.sending_chain_key.hex()}")
        print(f"[初始化] 设置后的接收链密钥: {self.receiving_chain_key.hex()}")
                
        self.session_initialized = True
        return shared_secret

    async def encrypt_message(self, plaintext: str) -> EncryptedMessage:
        """加密消息"""
        if not self.session_initialized:
            raise Exception("Session not initialized")
            
        print(f"\n[加密] 是否为发起方: {self.is_initiator}")
        print(f"[加密] 当前发送链密钥: {self.sending_chain_key.hex()}")
        print(f"[加密] 当前接收链密钥: {self.receiving_chain_key.hex()}")
            
        # 派生消息密钥
        message_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"message_key"
        ).derive(self.sending_chain_key)
        print(f"[加密] 派生的消息密钥: {message_key.hex()}")
        
        # 更新链密钥
        self.sending_chain_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"next_chain_key"
        ).derive(self.sending_chain_key)
        print(f"[加密] 更新后的发送链密钥: {self.sending_chain_key.hex()}")
        
        # 加密消息
        aesgcm = AESGCM(message_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        
        header = {
            'nonce': base64.b64encode(nonce).decode('utf-8'),
            'is_initiator': self.is_initiator
        }
        
        return EncryptedMessage(ciphertext=ciphertext, header=header)
    
    async def decrypt_message(self, encrypted_message: EncryptedMessage) -> str:
        """解密消息"""
        if not self.session_initialized:
            raise Exception("Session not initialized")
            
        print(f"\n[解密] 是否为发起方: {self.is_initiator}")
        print(f"[解密] 当前发送链密钥: {self.sending_chain_key.hex()}")
        print(f"[解密] 当前接收链密钥: {self.receiving_chain_key.hex()}")
            
        # 检查消息来源
        is_from_initiator = encrypted_message.header['is_initiator']
        use_receiving_key = (is_from_initiator and not self.is_initiator) or \
                          (not is_from_initiator and self.is_initiator)
        
        print(f"[解密] 消息来自发起方: {is_from_initiator}")
        print(f"[解密] 使用接收链密钥: {use_receiving_key}")
        
        # 使用正确的链密钥
        current_key = self.receiving_chain_key if use_receiving_key else self.sending_chain_key
        print(f"[解密] 选择的当前密钥: {current_key.hex()}")
        
        # 派生消息密钥
        message_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"message_key"
        ).derive(current_key)
        print(f"[解密] 派生的消息密钥: {message_key.hex()}")
        
        # 更新链密钥
        if use_receiving_key:
            self.receiving_chain_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"next_chain_key"
            ).derive(current_key)
            print(f"[解密] 更新后的接收链密钥: {self.receiving_chain_key.hex()}")
        else:
            self.sending_chain_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b"next_chain_key"
            ).derive(current_key)
            print(f"[解密] 更新后的发送链密钥: {self.sending_chain_key.hex()}")
        
        # 解密消息
        aesgcm = AESGCM(message_key)
        nonce = base64.b64decode(encrypted_message.header['nonce'])
        
        try:
            plaintext = aesgcm.decrypt(nonce, encrypted_message.ciphertext, None)
            return plaintext.decode('utf-8')
        except InvalidTag as e:
            print(f"[解密] 解密失败，密钥不匹配!")
            raise Exception("Message decryption failed")

    def _create_shared_key(self) -> bytes:
        """创建共享密钥用于初始化"""
        random_bytes = os.urandom(32)
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"shared_key"
        ).derive(random_bytes)
    
    def generate_identity_key(self) -> None:
        """生成身份密钥对"""
        self.identity_key = x25519.X25519PrivateKey.generate()
        self.identity_key_pub = self.identity_key.public_key()
    
    def generate_signed_prekey(self) -> None:
        """生成预签名密钥对"""
        self.signed_prekey = x25519.X25519PrivateKey.generate()
        self.signed_prekey_pub = self.signed_prekey.public_key()
    
    def generate_one_time_prekey(self) -> int:
        """生成一次性预密钥对"""
        key_id = len(self.one_time_prekeys)
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        self.one_time_prekeys[key_id] = (private_key, public_key)
        return key_id
    
    def _derive_keys(self, shared_secret: bytes, salt: bytes = None) -> Tuple[bytes, bytes]:
        """从共享密钥派生根密钥和链密钥"""
        if not salt:
            salt = os.urandom(32)
            
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,  # 32 bytes for each key
            salt=salt,
            info=b"Signal_Protocol_Keys"
        )
        
        derived_key = hkdf.derive(shared_secret)
        return derived_key[:32], derived_key[32:]  # root_key, chain_key
    
    def _derive_message_keys(self, chain_key: bytes) -> Tuple[bytes, bytes]:
        """从链密钥派生消息密钥和下一个链密钥"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=64,
            salt=None,
            info=b"Message_Keys"
        )
        
        derived_key = hkdf.derive(chain_key)
        return derived_key[:32], derived_key[32:]  # message_key, next_chain_key

# 使用示例
async def main():
    # 创建Alice和Bob的协议实例
    alice = SignalProtocol()
    bob = SignalProtocol()
    
    print("=== 初始化密钥 ===")
    # 生成身份密钥
    alice.generate_identity_key()
    bob.generate_identity_key()
    alice.generate_signed_prekey()
    bob.generate_signed_prekey()
    
    # 双方生成一次性预密钥
    alice_one_time_key_id = alice.generate_one_time_prekey()
    bob_one_time_key_id = bob.generate_one_time_prekey()
    
    print("Alice的初始链密钥:", alice.sending_chain_key and alice.sending_chain_key[:8].hex())
    print("Bob的初始链密钥:", bob.receiving_chain_key and bob.receiving_chain_key[:8].hex())
    
    print("\n=== 建立初始会话 ===")
    # Alice作为发起方初始化会话，使用Bob的公开一次性预密钥
    await alice.initiate_session(
        bob.identity_key_pub,
        bob.signed_prekey_pub,
        recipient_one_time_prekey=bob.one_time_prekeys[bob_one_time_key_id][1],
        is_initiator=True
    )
    
    # Bob作为响应方初始化会话，传入Alice的临时公钥，并使用自己的一次性预密钥
    await bob.initiate_session(
        alice.identity_key_pub,
        alice.signed_prekey_pub,
        recipient_ephemeral_key=alice.ephemeral_key_pub,
        own_one_time_prekey=bob.one_time_prekeys[bob_one_time_key_id][1],
        is_initiator=False
    )
    
    print("Alice 发送链密钥:", alice.sending_chain_key[:8].hex())
    print("Alice 接收链密钥:", alice.receiving_chain_key[:8].hex())
    print("Bob 发送链密钥:", bob.sending_chain_key[:8].hex())
    print("Bob 接收链密钥:", bob.receiving_chain_key[:8].hex())
    
    # 后续消息交换逻辑保持不变
    async def send_message(sender: SignalProtocol, receiver: SignalProtocol, message: str, round_num: int):
        print(f"\n=== 第 {round_num} 轮消息交换 ===")
        print(f"发送前链密钥: {sender.sending_chain_key[:8].hex()}")
        
        encrypted = await sender.encrypt_message(message)
        print(f"消息已加密，新的链密钥: {sender.sending_chain_key[:8].hex()}")
        
        decrypted = await receiver.decrypt_message(encrypted)
        print(f"消息已解密，接收方链密钥: {receiver.receiving_chain_key[:8].hex()}")
        
        print(f"原始消息: {message}")
        print(f"解密消息: {decrypted}")
        return encrypted, decrypted
    
    # 第一轮：Alice -> Bob
    await send_message(
        alice, bob,
        "Hello Bob! This is the first message in our secure chat.",
        1
    )
    
    # 第二轮：Bob -> Alice
    await send_message(
        bob, alice,
        "Hi Alice! Received your message. This is my response.",
        2
    )
    
    # 第三轮：Alice -> Bob
    await send_message(
        alice, bob,
        "Great! The double ratchet is working. Here's another message.",
        3
    )
    
    # 第四轮：Bob -> Alice
    await send_message(
        bob, alice,
        "Perfect! Each message gets a new chain key for perfect forward secrecy.",
        4
    )
    
    print("\n=== 最终密钥状态 ===")
    print("Alice发送链密钥:", alice.sending_chain_key[:8].hex())
    print("Bob接收链密钥:", bob.receiving_chain_key[:8].hex())
    print("Alice接收链密钥:", alice.receiving_chain_key[:8].hex())
    print("Bob发送链密钥:", bob.sending_chain_key[:8].hex())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())