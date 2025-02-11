import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.asymmetric import ed25519
from typing import Optional, List, Tuple
from chate2e.crypto.AAA import *

class X3DHHelper:
    def __init__(self, ecdh_helper, kdf_helper):
        self.ecdh_helper = ecdh_helper
        self.kdf_helper = kdf_helper

    def perform_x3dh(self, alice_priv_key, alice_pub_key, bob_priv_key, bob_pub_key, identity_key, ephemeral_key):
        """
        执行 X3DH 协议，交换共享密钥。
        :param alice_priv_key: Alice 的私钥
        :param alice_pub_key: Alice 的公钥
        :param bob_priv_key: Bob 的私钥
        :param bob_pub_key: Bob 的公钥
        :param identity_key: 共享的身份公钥
        :param ephemeral_key: 共享的临时公钥
        :return: 共享密钥（由双方计算得出）
        """
        # 1. Alice 计算共享密钥
        alice_shared_secret = self.ecdh_helper.ecdhe(bob_pub_key, alice_priv_key)  # Alice的公钥与Bob的私钥交换
        bob_shared_secret = self.ecdh_helper.ecdhe(alice_pub_key, bob_priv_key)  # Bob的公钥与Alice的私钥交换
        
        # 2. Alice 和 Bob 共同计算共享密钥
        combined_secret = alice_shared_secret + bob_shared_secret
        
        # 3. 用身份公钥（identity_key）与临时密钥（ephemeral_key）进行密钥派生
        root_key = self.kdf_helper.hkdf(combined_secret, 64, salt=None, info=b"X3DH")  # 派生根密钥
        
        # 4. 返回计算的根密钥
        return root_key


class DoubleRatchet:
    def __init__(self, kdf_helper):
        self.kdf_helper = kdf_helper

    def derive_keys(self, root_key: bytes, dh_output: bytes) -> Tuple[bytes, bytes]:
        """
        使用根密钥和 DH 输出，派生新密钥。
        :param root_key: 根密钥
        :param dh_output: 由 DH 协商得出的输出
        :return: 新的根密钥和链密钥
        """
        new_root_key, chain_key = self.kdf_helper.derive_root_and_chain_keys(root_key, dh_output)
        return new_root_key, chain_key

    def ratchet_step(self, chain_key: bytes) -> Tuple[bytes, bytes]:
        """
        双棘算法中的步骤，返回新的链密钥和消息密钥。
        :param chain_key: 当前链密钥
        :return: 新的链密钥和消息密钥
        """
        new_chain_key, message_key = self.kdf_helper.derive_message_key(chain_key)
        return new_chain_key, message_key


class TestCryptoFlow:
    def __init__(self):
        # 初始化帮助类
        self.ecdh_helper = ECDHHelper()
        self.kdf_helper = KDFHelper()
        self.x3dh_helper = X3DHHelper(self.ecdh_helper, self.kdf_helper)
        self.double_ratchet = DoubleRatchet(self.kdf_helper)
        
    def test_crypto_flow(self):
        # 1. Alice 和 Bob 分别生成密钥对
        alice_priv_key = self.ecdh_helper.create_key_pair()
        bob_priv_key = self.ecdh_helper.create_key_pair()
        
        # 2. 假设双方都知道对方的身份公钥和临时公钥
        alice_identity_priv_key = self.ecdh_helper.create_key_pair()
        bob_identity_priv_key = self.ecdh_helper.create_key_pair()
        
        alice_identity_pub_key = self.ecdh_helper.export_x25519_public_key(alice_identity_priv_key)
        bob_identity_pub_key = self.ecdh_helper.export_x25519_public_key(bob_identity_priv_key)

        alice_ephemeral_priv_key = self.ecdh_helper.create_key_pair()
        bob_ephemeral_priv_key = self.ecdh_helper.create_key_pair()

        alice_ephemeral_pub_key = self.ecdh_helper.export_x25519_public_key(alice_ephemeral_priv_key)
        bob_ephemeral_pub_key = self.ecdh_helper.export_x25519_public_key(bob_ephemeral_priv_key)

        # 3. Alice 和 Bob 执行 X3DH 协议计算共享密钥
        # 需要两个身份公钥和临时公钥
        root_key = self.x3dh_helper.perform_x3dh(
            alice_priv_key, bob_ephemeral_pub_key, bob_priv_key, alice_ephemeral_pub_key,
            bob_identity_pub_key, alice_identity_pub_key
        )

        # 4. 双棘算法开始
        # 交换的根密钥作为起始密钥
        root_key, chain_key = self.double_ratchet.derive_keys(root_key, b"dh_output")  # dh_output 代表每次的 DH 输出

        # 5. 进行消息发送和接收
        new_chain_key, message_key = self.double_ratchet.ratchet_step(chain_key)
        
        # 加密和解密消息
        message = b"Hello Bob, this is Alice"
        
        # 发送消息
        encrypted_message = AESHelper().encrypt_gcm(message_key, message, os.urandom(12))  # 使用 GCM 加密
        
        # 接收消息并解密
        decrypted_message = AESHelper().decrypt_gcm(message_key, encrypted_message[:-16], os.urandom(12), encrypted_message[-16:])
        
        print(f"Alice sent: {message.decode()}")
        print(f"Bob received: {decrypted_message.decode()}")
        
        assert message == decrypted_message  # 确保消息一致


# 初始化并执行测试
test = TestCryptoFlow()
test.test_crypto_flow()
