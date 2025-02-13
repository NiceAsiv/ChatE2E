from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class MACHelper:
    @staticmethod
    def sign(data: bytes, key: bytes) -> bytes:
        """
        使用 HMAC-SHA256 进行签名，生成 MAC 值。
        :param key: 密钥字节
        :param data: 待签名数据
        :return: 生成的 MAC 值
        """
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(data)
        return h.finalize()
    
    @staticmethod
    def verify(key: bytes, data: bytes, mac: bytes, length: int) -> None:
        """
        验证 MAC 是否正确。
        :param data: 被验证的数据
        :param key: 用于生成 MAC 的密钥
        :param mac: 需要验证的 MAC 值
        :param length: MAC 长度
        :raises ValueError: 如果 MAC 校验失败
        """
        calculated_mac = MACHelper.sign(data, key)
        if len(mac) != length or len(calculated_mac) < length:
            raise ValueError("Bad MAC length")

        if not MACHelper.constant_time_compare(calculated_mac[:length], mac):
            raise ValueError("Bad MAC")
    
    @staticmethod
    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """
        使用常量时间比较两个字节串是否相等，防止时序攻击。
        :param a: 字节串1
        :param b: 字节串2
        :return: 是否相等
        """
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0
    
    @staticmethod
    def ed25519_sign(priv_key_bytes: bytes, message: bytes) -> bytes:
        """
        Ed25519签名。
        :param priv_key_bytes: 32字节的Ed25519私钥
        :param message: 待签名消息
        :return: 签名结果
        """
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_key_bytes)
        return private_key.sign(message)
    
    @staticmethod
    def ed25519_verify(pub_key_bytes: bytes, msg: bytes, sig: bytes) -> bool:
        """
        Ed25519验签。
        :param pub_key_bytes: 32字节的Ed25519公钥
        :param msg: 已签名的消息
        :param sig: 签名值
        :return: 验证结果，True或抛出异常
        """
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)
        try:
            public_key.verify(sig, msg)
            return True
        except Exception:
            return False