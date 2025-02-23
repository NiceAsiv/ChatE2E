from typing import Optional, Union
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidKey

class MACHelper:
    # 定义类常量
    MINIMUM_KEY_LENGTH = 8  # 最小密钥长度（字节）
    DEFAULT_HASH = hashes.SHA256()
    
    @staticmethod
    def sign(data: bytes, 
            key: bytes, 
            hash_algorithm: hashes.HashAlgorithm = DEFAULT_HASH) -> bytes:
        """
        使用 HMAC 进行签名，生成 MAC 值。
        
        Args:
            data: 待签名数据
            key: 密钥字节
            hash_algorithm: 哈希算法，默认为 SHA256
            
        Returns:
            bytes: 生成的 MAC 值
            
        Raises:
            ValueError: 如果密钥长度小于最小要求
            TypeError: 如果输入类型不正确
        """
        if not isinstance(key, bytes) or not isinstance(data, bytes):
            raise TypeError("Key and data must be bytes")
            
        if len(key) < MACHelper.MINIMUM_KEY_LENGTH:
            raise ValueError(f"Key length must be at least {MACHelper.MINIMUM_KEY_LENGTH} bytes")
            
        try:
            h = hmac.HMAC(key, hash_algorithm, backend=default_backend())
            h.update(data)
            return h.finalize()
        except Exception as e:
            raise ValueError(f"MAC generation failed: {str(e)}")
    
    @staticmethod
    def verify(key: bytes, 
              data: bytes, 
              mac: bytes, 
              length: Optional[int] = None,
              hash_algorithm: hashes.HashAlgorithm = DEFAULT_HASH) -> None:
        """
        验证 MAC 是否正确。
        
        Args:
            key: 用于生成 MAC 的密钥
            data: 被验证的数据
            mac: 需要验证的 MAC 值
            length: MAC 长度，如果为None则使用完整长度
            hash_algorithm: 哈希算法，默认为 SHA256
            
        Raises:
            ValueError: 如果MAC验证失败
            TypeError: 如果输入类型不正确
        """
        try:
            calculated_mac = MACHelper.sign(data, key, hash_algorithm)
            mac_length = length or len(calculated_mac)
            
            if len(mac) != mac_length or len(calculated_mac) < mac_length:
                raise ValueError("Bad MAC")
                
            if not MACHelper.constant_time_compare(
                calculated_mac[:mac_length], 
                mac[:mac_length]
            ):
                raise ValueError("Bad MAC")
                
        except Exception as e:
            raise ValueError("Bad MAC")
        
    @staticmethod
    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """
        使用常量时间比较两个字节串，防止时序攻击。
        
        使用按位异或和按位或操作确保比较时间与输入长度无关。
        """
        if not (isinstance(a, bytes) and isinstance(b, bytes)):
            raise TypeError("Inputs must be bytes")
            
        if len(a) != len(b):
            return False
            
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0
    
    @staticmethod
    def ed25519_sign(priv_key_bytes: bytes, message: bytes) -> bytes:
        """
        使用Ed25519进行签名。
        
        Args:
            priv_key_bytes: 32字节的Ed25519私钥
            message: 待签名消息
            
        Returns:
            bytes: 签名结果
            
        Raises:
            ValueError: 如果私钥长度不正确或签名失败
        """
        if len(priv_key_bytes) != 32:
            raise ValueError("Ed25519 private key must be 32 bytes")
            
        try:
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_key_bytes)
            return private_key.sign(message)
        except Exception as e:
            raise ValueError(f"Ed25519 signing failed: {str(e)}")
    
    @staticmethod
    def ed25519_verify(pub_key_bytes: bytes, msg: bytes, sig: bytes) -> bool:
        """
        验证Ed25519签名。
        
        Args:
            pub_key_bytes: 32字节的Ed25519公钥
            msg: 已签名的消息
            sig: 签名值
            
        Returns:
            bool: 验证是否成功
        """
        if len(pub_key_bytes) != 32:
            return False
            
        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)
            public_key.verify(sig, msg)
            return True
        except Exception:
            return False