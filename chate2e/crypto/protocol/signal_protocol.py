from typing import Dict, Tuple, Optional
from cryptography.hazmat.primitives.asymmetric import x25519
from chate2e.crypto.crypto_helper import CryptoHelper
from chate2e.crypto.mac_helper import MACHelper
from cryptography.hazmat.primitives import serialization

from chate2e.model.bundle import Bundle, LocalBundle
from chate2e.model.key_pair import KeyPair
from chate2e.model.message import Message, MessageType, Encryption, X3DHparams
from chate2e.crypto.protocol.ratchet import DoubleRatchet
import base64

class SignalProtocol:
    def __init__(self):
        self.crypto_helper = CryptoHelper()
        self.mac_helper = MACHelper()
        self.ratchet = DoubleRatchet()

        # 身份密钥对
        self.identity_key = None
        self.identity_key_pub = None
        
        # 预签名密钥对
        self.signed_prekey = None
        self.signed_prekey_pub = None
        self.signed_prekey_signature = None

        # 一次性预密钥集合
        self.MAX_ONE_TIME_PREKEYS = 10
        # self.one_time_prekeys: Dict[int, Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]] = {}
        self.one_time_prekeys = []
        self.one_time_prekeys_pub = []

        # 会话密钥
        self.root_key = None
        self.sending_chain_key = None
        self.receiving_chain_key = None

        #存储对方的密钥Bundle user_id: Bundle
        self.peer_key_bundle: Dict[str ,Bundle] = {}

        # 会话状态
        self.session_initialized = False
        self.is_initiator = False

        self.session_id = None
        self.user_id = None
        self.peer_id = None
    
    def initialize_identity(self, user_id: str):
        """初始化用户身份"""
        self.user_id = user_id
        self.identity_key = self.crypto_helper.generate_priv_x25519_keypair()
        self.identity_key_pub = self.identity_key.public_key()
        self.signed_prekey = self.crypto_helper.generate_priv_x25519_keypair()
        self.signed_prekey_pub = self.signed_prekey.public_key()
        self.signed_prekey_signature = self.mac_helper.sign(
            self.crypto_helper.export_x25519_public_key(self.signed_prekey_pub),
            self.crypto_helper.export_x25519_private_key(self.identity_key)
        )
        self.init_one_time_prekeys()

    def init_one_time_prekeys(self):
        """
        初始化一次性预密钥
        """
        for _ in range(self.MAX_ONE_TIME_PREKEYS):
            private_key = self.crypto_helper.generate_priv_x25519_keypair()
            public_key = private_key.public_key()
            self.one_time_prekeys.append((private_key, public_key))
            self.one_time_prekeys_pub.append(public_key)

    def set_peer_bundle(self, peer_id:str, bundle:Bundle):
        """设置对方的密钥Bundle"""
        self.peer_key_bundle[peer_id] = bundle


    def create_bundle(self) -> Bundle:
        """创建包含公钥信息的Bundle

        Returns:
            Bundle对象，包含身份公钥、签名预密钥和一次性预密钥
        """
        if not self.identity_key_pub or not self.signed_prekey_pub:
            raise ValueError("Identity key or signed prekey not generated")

        # 导出公钥为原始字节格式
        identity_key_bytes = self.crypto_helper.export_x25519_public_key(self.identity_key_pub)
        signed_prekey_bytes = self.crypto_helper.export_x25519_public_key(self.signed_prekey_pub)

        # 收集所有一次性预密钥的公钥
        one_time_prekeys = frozenset(
            self.crypto_helper.export_x25519_public_key(key)
            for key in self.one_time_prekeys_pub
        )

        return Bundle(
            identity_key_pub=identity_key_bytes,
            signed_pre_key_pub=signed_prekey_bytes,
            signed_pre_key_signature=self.signed_prekey_signature,
            one_time_pre_keys_pub=one_time_prekeys
        )

    def create_local_bundle(self) -> LocalBundle:
        """创建本地Bundle"""
        if not self.identity_key or not self.signed_prekey:
            raise ValueError("Identity key or signed prekey not generated")
        # 导出密钥为原始字节格式
        identity_key_bytes = self.crypto_helper.export_x25519_private_key(self.identity_key)
        identity_key_pub_bytes = self.crypto_helper.export_x25519_public_key(self.identity_key_pub)
        identity_key_pair = KeyPair(private_key=identity_key_bytes, public_key=identity_key_pub_bytes)

        signed_prekey_bytes = self.crypto_helper.export_x25519_private_key(self.signed_prekey)
        signed_prekey_pub_bytes = self.crypto_helper.export_x25519_public_key(self.signed_prekey_pub)
        signed_pre_key_pair = KeyPair(private_key=signed_prekey_bytes, public_key=signed_prekey_pub_bytes)

        one_time_pre_key_pairs = frozenset(
            KeyPair(
                private_key=self.crypto_helper.export_x25519_private_key(priv),
                public_key=self.crypto_helper.export_x25519_public_key(pub)
            )
            for priv, pub in self.one_time_prekeys
        )

        return LocalBundle(
            identity_key_pair=identity_key_pair,
            signed_pre_key_pair= signed_pre_key_pair,
            signed_pre_key_signature=self.signed_prekey_signature,
            one_time_pre_key_pairs=one_time_pre_key_pairs
        )

    def load_signal_from_local_bundle(self, local_bundle: LocalBundle):
        """加载本地Bundle"""
        # 从字节序列导入身份密钥对
        self.identity_key = self.crypto_helper.import_x25519_private_key(local_bundle.identity_key_pair.private_key)
        self.identity_key_pub = self.crypto_helper.import_x25519_public_key(local_bundle.identity_key_pair.public_key)

        # 从字节序列导入预签名密钥对
        self.signed_prekey = self.crypto_helper.import_x25519_private_key(local_bundle.signed_pre_key_pair.private_key)
        self.signed_prekey_pub = self.crypto_helper.import_x25519_public_key(
            local_bundle.signed_pre_key_pair.public_key)

        # 直接设置签名
        self.signed_prekey_signature = local_bundle.signed_pre_key_signature

        # 从字节序列导入一次性预密钥对
        self.one_time_prekeys = []
        self.one_time_prekeys_pub = []

        for key_pair in local_bundle.one_time_pre_key_pairs:
            priv_key = self.crypto_helper.import_x25519_private_key(key_pair.private_key)
            pub_key = self.crypto_helper.import_x25519_public_key(key_pair.public_key)
            self.one_time_prekeys.append((priv_key, pub_key))
            self.one_time_prekeys_pub.append(pub_key)
    
    def initiate_session(self,
                             peer_id: str,
                             session_id: str,
                             recipient_identity_key: x25519.X25519PublicKey,
                             recipient_signed_prekey: x25519.X25519PublicKey,
                             recipient_ephemeral_key: Optional[x25519.X25519PublicKey] = None,
                             recipient_one_time_prekey: Optional[x25519.X25519PublicKey] = None,
                             own_one_time_prekey: Optional[x25519.X25519PublicKey] = None,
                             is_initiator: bool = True) -> Message:
        """
        根据 Signal 协议计算共享密钥：
        DH1 = DH(身份私钥, 对方签名预密钥公钥)
        DH2 = DH(本地临时密钥, 对方身份公钥) 或 DH(对方身份公钥, 对方传来的临时公钥)
        DH3 = DH(本地临时密钥, 对方签名预密钥公钥) 或 DH(对方签名预密钥, 对方传来的临时公钥)
        DH4 = DH(身份私钥, 对方一次性预密钥公钥) （可选）
        SK  = HKDF(DH1 || DH2 || DH3 || DH4)
        
        :param peer_id: 对方用户ID
        :param session_id: 会话ID
        :param recipient_identity_key: 对方的身份密钥
        :param recipient_signed_prekey: 对方的预签名密钥
        :param recipient_ephemeral_key: 对方的临时密钥
        :param own_one_time_prekey: 自己的一次性预密钥
        :param recipient_one_time_prekey: 对方的一次性预密钥
        :param is_initiator: 是否为发起方
        :return: 共享密钥
        """
        print(f"\n[初始化] 开始会话初始化 (是否为发起方: {is_initiator})")
        
        self.is_initiator = is_initiator
        self.peer_id = peer_id
        self.session_id = session_id
        x3dh_params = None

        # 计算共享密钥
        if is_initiator:
            # 生成临时密钥对
            self.ephemeral_key = self.crypto_helper.generate_priv_x25519_keypair()
            self.ephemeral_key_pub = self.ephemeral_key.public_key()
            
            # 计算DH值
            dh1 = self.crypto_helper.ecdh(self.identity_key, recipient_signed_prekey)
            dh2 = self.crypto_helper.ecdh(self.ephemeral_key, recipient_identity_key)
            dh3 = self.crypto_helper.ecdh(self.ephemeral_key, recipient_signed_prekey)
            
            shared_secret = dh1 + dh2 + dh3
            
            if recipient_one_time_prekey:
                dh4 = self.crypto_helper.ecdh(self.ephemeral_key, recipient_one_time_prekey)
                shared_secret += dh4
            
            print(f"[初始化] 发起方最终共享密钥: {shared_secret.hex()}")

                
            # 创建会话初始化消息
            x3dh_params = X3DHparams(
                identity_key_pub= self.crypto_helper.export_x25519_public_key(self.identity_key_pub),
                signed_pre_key_pub= self.crypto_helper.export_x25519_public_key(self.signed_prekey_pub),
                one_time_pre_keys_pub= self.crypto_helper.export_x25519_public_key(recipient_one_time_prekey),
                ephemeral_key_pub= self.crypto_helper.export_x25519_public_key(self.ephemeral_key_pub)
            )

        else:
            #响应方必须传入发起方的临时密钥对
            if not recipient_ephemeral_key:
                raise ValueError("响应方初始化时必须提供发起方的临时公钥")
            
            # 计算DH值
            dh1 = self.crypto_helper.ecdh(self.signed_prekey, recipient_identity_key)
            dh2 = self.crypto_helper.ecdh(self.identity_key, recipient_ephemeral_key)
            dh3 = self.crypto_helper.ecdh(self.signed_prekey, recipient_ephemeral_key)
            
            shared_secret = dh1 + dh2 + dh3
            print(f"[初始化] 响应方生成共享密钥: {shared_secret.hex()}")
            
            if own_one_time_prekey:
                # 使用响应方的一次性预密钥
                for index, (priv, pub) in enumerate(self.one_time_prekeys):
                    # 比较公钥原始字节
                    if pub.public_bytes(encoding=serialization.Encoding.Raw,
                                    format=serialization.PublicFormat.Raw) == \
                    own_one_time_prekey.public_bytes(encoding=serialization.Encoding.Raw,
                                                    format=serialization.PublicFormat.Raw):
                        dh4 = self.crypto_helper.ecdh(priv, recipient_ephemeral_key)
                        shared_secret += dh4
                        # 使用后删除该一次性预密钥
                        self.one_time_prekeys.pop(index)
                        self.one_time_prekeys_pub.pop(index)
                        break
            
            print(f"[初始化] 响应方最终共享密钥: {shared_secret.hex()}")

                    
        # 派生根密钥和链密钥
        self.root_key = self.crypto_helper.hkdf(shared_secret, 32, info=b"root_key")
        print(f"[初始化] 生成的派生根密钥: {self.root_key.hex()}")

        # 为发送和接收派生初始链密钥
        self.root_key, initial_sending_key, initial_receiving_key = \
            self.ratchet.root_ratchet(shared_secret, self.root_key)

        # 根据角色分配链密钥 
        if is_initiator:
            self.sending_chain_key = initial_sending_key
            self.receiving_chain_key = initial_receiving_key
        else:
            self.sending_chain_key = initial_receiving_key
            self.receiving_chain_key = initial_sending_key
            
        print(f"[初始化] 发送链密钥: {self.sending_chain_key.hex()}")
        print(f"[初始化] 接收链密钥: {self.receiving_chain_key.hex()}")

        self.session_initialized = True

        # 创建初始化消息
        return Message(
            message_id=Message.generate_id(),
            sender_id=self.user_id,
            receiver_id=peer_id,
            session_id=self.session_id,
            message_type=MessageType.INITIATE if is_initiator else MessageType.ACK_INITIATE,
            encrypted_content=b"session_init",  # Add a meaningful init message
            X3DHparams=x3dh_params,
            encryption=None  # Explicitly set encryption to None for init messages
        )
        # return shared_secret


        
    def encrypt_message(self, plaintext: str) -> Message:
        """加密消息"""
        if not self.session_initialized:
            raise Exception("Session not initialized")

        print(f"[加密] 明文: {plaintext}")
        print(f"[加密] 明文长度: {len(plaintext)}")

        # 使用发送链棘轮生成消息密钥和新的发送链密钥
        message_key, self.sending_chain_key = \
            self.ratchet.sending_ratchet(self.sending_chain_key)
            
        print(f"[加密] 生成的消息密钥: {message_key.hex()}")
        print(f"[加密] 新的发送链密钥: {self.sending_chain_key.hex()}")

        # 生成随机IV
        iv = self.crypto_helper.get_random_bytes(12)
        
        # 使用AES-GCM加密
        plaintext_bytes = plaintext.encode()
        print(f"[加密] 明文bytes长度: {len(plaintext_bytes)}")
        
        ciphertext, tag = self.crypto_helper.encrypt_aes_gcm(message_key, 
                                                     plaintext_bytes, 
                                                     iv)
        
        print(f"[加密] 密文长度: {len(ciphertext)}")
        print(f"[加密] 标签长度: {len(tag)}")
        
        # 创建加密参数，使用bytes类型
        encryption = Encryption(
            algorithm="AES-GCM",
            iv=iv,
            tag=tag,
            is_initiator=self.is_initiator
        )
        
        # 创建加密消息，使用bytes
        return Message(
            message_id=Message.generate_id(),
            sender_id=self.user_id,
            session_id=self.session_id,
            receiver_id=self.peer_id,
            encryption=encryption,
            message_type=MessageType.MESSAGE,
            encrypted_content=ciphertext
        )

    def decrypt_message(self, message: Message) -> str:
        """解密消息"""
        if not self.session_initialized:
            raise Exception("Session not initialized")
            
        # 检查消息来源和密钥选择
        is_from_initiator = message.encryption.is_initiator
        use_receiving_key = (is_from_initiator and not self.is_initiator) or \
                          (not is_from_initiator and self.is_initiator)

        # 选择正确的链密钥
        current_key = self.receiving_chain_key if use_receiving_key else self.sending_chain_key

        # 使用接收链棘轮派生消息密钥
        message_key, new_chain_key = self.ratchet.receiving_ratchet(current_key)
        
        print(f"[解密] 生成的消息密钥: {message_key.hex()}")
        print(f"[解密] 旧的链密钥: {current_key.hex()}")
        print(f"[解密] 新的链密钥: {new_chain_key.hex()}")

        try:
            # encryption对象中的iv/tag已经是bytes类型（在from_dict时已解码）
            iv = message.encryption.iv
            tag = message.encryption.tag
            # encrypted_content 已经在 Message.from_dict 中被解码为 bytes
            ciphertext = message.encrypted_content
            
            print(f"[解密] IV类型: {type(iv)}, 长度: {len(iv) if isinstance(iv, bytes) else 'N/A'}")
            print(f"[解密] Tag类型: {type(tag)}, 长度: {len(tag) if isinstance(tag, bytes) else 'N/A'}")
            print(f"[解密] 密文长度: {len(ciphertext)}")
            
            # 解密消息
            plaintext = self.crypto_helper.decrypt_aes_gcm(
                message_key,
                ciphertext,
                iv,
                tag
            )
            
            # ✅ 只有解密成功才更新链密钥
            if use_receiving_key:
                self.receiving_chain_key = new_chain_key
            else:
                self.sending_chain_key = new_chain_key
            
            print(f"[解密] ✓ GCM解密成功")
            print(f"[解密] 明文bytes长度: {len(plaintext)}")
            print(f"[解密] 明文bytes前20字节: {plaintext[:20]}")
            
            decoded = plaintext.decode('utf-8')
            print(f"[解密] ✓ UTF-8解码成功: {decoded}")
            return decoded
            
        except Exception as e:
            print(f"[解密] ✗ 解密失败，链密钥保持不变: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Message decryption failed: {str(e)}")
        
        
#使用示例
async def main():
    # Create protocol instances
    alice = SignalProtocol()
    bob = SignalProtocol()

    # Initialize identities
    alice.initialize_identity("u001")
    bob.initialize_identity("u002")

    # Create bundles
    alice_bundle = alice.create_bundle()
    bob_bundle = bob.create_bundle()

    print("\n=== 密钥束信息 ===")
    print("Alice的一次性预密钥数量:", len(alice.one_time_prekeys))
    print("Bob的一次性预密钥数量:", len(bob.one_time_prekeys))

    print("Alice的初始链密钥:", alice.sending_chain_key and alice.sending_chain_key[:8].hex())
    print("Bob的初始链密钥:", bob.receiving_chain_key and bob.receiving_chain_key[:8].hex())

    print("\n=== 建立初始会话 ===")

    # Store each other's bundles
    alice.set_peer_bundle("u002", bob_bundle)
    bob.set_peer_bundle("u001", alice_bundle)

    # Alice initiates session
    init_message = alice.initiate_session(
        peer_id="u002",
        session_id="session1",
        recipient_identity_key=bob.identity_key_pub,
        recipient_signed_prekey=bob.signed_prekey_pub,
        recipient_one_time_prekey=bob.one_time_prekeys_pub[0],
        is_initiator=True
    )

    # Bob responds to session initiation
    bob.initiate_session(
        peer_id="u001",
        session_id="session1",
        recipient_identity_key=alice.identity_key_pub,
        recipient_signed_prekey=alice.signed_prekey_pub,
        recipient_ephemeral_key=alice.ephemeral_key_pub,
        own_one_time_prekey=bob.one_time_prekeys_pub[0],
        is_initiator=False
    )

    print("Alice 发送链密钥:", alice.sending_chain_key[:8].hex())
    print("Alice 接收链密钥:", alice.receiving_chain_key[:8].hex())
    print("Bob 发送链密钥:", bob.sending_chain_key[:8].hex())
    print("Bob 接收链密钥:", bob.receiving_chain_key[:8].hex())
    
    print("\n=== 加密和解密消息 ===")
    
    async def send_message(sender:SignalProtocol, receiver:SignalProtocol, message:str ,round_num:int):
        
        print(f"\n=== 第 {round_num} 轮消息交换 ===")
        print(f"发送前链密钥: {sender.sending_chain_key[:8].hex()}")
        
        encrypted = sender.encrypt_message(message)
        print(f"消息已加密，新的链密钥: {sender.sending_chain_key[:8].hex()}")
        
        decrypted = receiver.decrypt_message(encrypted)
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