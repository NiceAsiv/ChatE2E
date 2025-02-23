from typing import Tuple
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from chate2e.crypto.crypto_helper import CryptoHelper

class DoubleRatchet:
    """双棘轮(Double Ratchet)实现"""
    def __init__(self):
        self.crypto_helper = CryptoHelper()

    def root_ratchet(self, shared_secret: bytes, root_key: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        根链棘轮(Root Chain Ratchet)
        用于生成新的根密钥和链密钥
        
        Args:
            shared_secret: 共享密钥
            root_key: 当前根密钥
            
        Returns:
            (新根密钥, 新发送链密钥, 新接收链密钥)
        """
        # 使用当前根密钥作为盐值派生新密钥
        derived_keys = self.crypto_helper.hkdf(
            root_key,
            96,
            salt=shared_secret,
            info=b"double_ratchet"
        )
        
        return (
            derived_keys[0:32],    # 新的根密钥
            derived_keys[32:64],   # 新的发送链密钥
            derived_keys[64:96]    # 新的接收链密钥
        )

    def sending_ratchet(self , current_sending_key: bytes) -> Tuple[bytes, bytes]:
        """
        发送链棘轮(Sending Chain Ratchet)
        用于生成消息密钥和更新发送链密钥
        
        Args:
            current_sending_key: 当前发送链密钥
            
        Returns:
            (消息密钥, 新发送链密钥)
        """
        # 生成消息密钥
        message_key = self.crypto_helper.hkdf(
            current_sending_key,
            32,
            info=b"message_key"
        )
        
        # 更新发送链密钥
        next_sending_key = self.crypto_helper.hkdf(
            current_sending_key,
            32,
            info=b"next_chain_key"
        )
        
        return message_key, next_sending_key

    def receiving_ratchet(self , current_receiving_key: bytes) -> Tuple[bytes, bytes]:
        """
        接收链棘轮(Receiving Chain Ratchet)
        用于生成消息密钥和更新接收链密钥
        
        Args:
            current_receiving_key: 当前接收链密钥
            
        Returns:
            (消息密钥, 新接收链密钥)
        """
        # 生成消息密钥
        message_key = self.crypto_helper.hkdf(
            current_receiving_key,
            32,
            info=b"message_key"
        )
        
        # 更新接收链密钥
        next_receiving_key = self.crypto_helper.hkdf(
            current_receiving_key,
            32,
            info=b"next_chain_key"
        )
        
        return message_key, next_receiving_key
