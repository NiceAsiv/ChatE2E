import os
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.backends import default_backend

class CryptoHelper:
    """
    加密辅助类，提供HMAC签名、AES加解密、SHA-512哈希、KDF、X25519、Ed25519等方法。
    """

    def sign_hmac(self, key: bytes, data: bytes) -> bytes:
        """
        使用HMAC-SHA256进行签名，生成MAC值。
        :param key: 密钥字节
        :param data: 待签名数据
        :return: 生成的MAC值
        """
        h = hmac.HMAC(key, hashes.SHA256(), backend=default_backend())
        h.update(data)
        return h.finalize()

    def get_random_bytes(self, size: int) -> bytes:
        """
        生成指定长度的随机字节。
        :param size: 随机字节长度
        :return: 生成的随机字节
        """
        return os.urandom(size)

    def encrypt_aes_cbc(self, key: bytes, data: bytes, iv: bytes) -> bytes:
        """
        使用AES-CBC模式进行加密。
        :param key: 原始密钥
        :param data: 待加密数据
        :param iv: 初始向量
        :return: 加密结果
        """
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(data) + encryptor.finalize()

    def decrypt_aes_cbc(self, key: bytes, data: bytes, iv: bytes) -> bytes:
        """
        使用AES-CBC模式进行解密。
        :param key: 原始密钥
        :param data: 待解密数据
        :param iv: 初始向量
        :return: 解密结果
        """
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()

    def hash_sha512(self, data: bytes) -> bytes:
        """
        计算SHA-512摘要。
        :param data: 输入数据
        :return: SHA-512哈希值
        """
        digest = hashes.Hash(hashes.SHA512(), backend=default_backend())
        digest.update(data)
        return digest.finalize()

    def kdf(self, input_data: bytes, salt: bytes, info: bytes) -> list:
        """
        根据自定义逻辑进行密钥派生，模拟示例KDF过程。
        :param input_data: 初始输入
        :param salt: 盐（32字节）
        :param info: 附加信息
        :return: 派生出的中间结果列表
        """
        if len(salt) != 32:
            raise ValueError("Got salt of incorrect length")

        prk = self.sign_hmac(salt, input_data)
        info_buffer_1 = info + b'\x01'
        t1 = self.sign_hmac(prk, info_buffer_1)
        info_buffer_2 = t1 + info + b'\x02'
        t2 = self.sign_hmac(prk, info_buffer_2)
        return [t1, t2]

    def create_key_pair(self, priv_key: bytes = None) -> x25519.X25519PrivateKey:
        """
        生成或使用给定私钥创建X25519密钥对。
        :param priv_key: 可选的32字节私钥
        :return: X25519私钥对象
        """
        if priv_key is None:
            return x25519.X25519PrivateKey.generate()
        return x25519.X25519PrivateKey.from_private_bytes(priv_key)

    def ecdhe(self, pub_key_bytes: bytes, priv_key: x25519.X25519PrivateKey) -> bytes:
        """
        执行X25519的ECDH操作。
        :param pub_key_bytes: 对方的公钥字节
        :param priv_key: 自己的X25519私钥
        :return: 协商得出的共享密钥
        """
        peer_public_key = x25519.X25519PublicKey.from_public_bytes(pub_key_bytes)
        return priv_key.exchange(peer_public_key)

    def ed25519_sign(self, priv_key_bytes: bytes, message: bytes) -> bytes:
        """
        Ed25519签名。
        :param priv_key_bytes: 32字节的Ed25519私钥
        :param message: 待签名消息
        :return: 签名结果
        """
        private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_key_bytes)
        return private_key.sign(message)

    def ed25519_verify(self, pub_key_bytes: bytes, msg: bytes, sig: bytes) -> bool:
        """
        Ed25519验签。
        :param pub_key_bytes: 32字节的Ed25519公钥
        :param msg: 已签名的消息
        :param sig: 签名值
        :return: 验证结果，True或抛出异常
        """
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_key_bytes)
        public_key.verify(sig, msg)
        return True

    def verify_mac(self, data: bytes, key: bytes, mac: bytes, length: int) -> None:
        """
        验证MAC是否正确。
        :param data: 被验证的数据
        :param key: 用于生成MAC的密钥
        :param mac: 需要验证的MAC值
        :param length: MAC长度
        :return: 无返回，验证失败会抛出异常
        """
        calculated_mac = self.sign_hmac(key, data)
        if len(mac) != length or len(calculated_mac) < length:
            raise ValueError("Bad MAC length")

        result = 0
        for a, b in zip(calculated_mac[:length], mac):
            result |= a ^ b
        if result != 0:
            raise ValueError("Bad MAC")
        
        
    def pad_pkcs7(self, data: bytes, block_size: int) -> bytes:
        """
        使用PKCS7填充数据。
        :param data: 待填充数据
        :param block_size: 块大小
        :return: 填充后的数据
        """
        padding_length = block_size - (len(data) % block_size)
        padding = bytes([padding_length] * padding_length)
        return data + padding
    
    def unpad_pkcs7(self, padded_data: bytes) -> bytes:
        """
        使用PKCS7解除填充。
        :param data: 待解除填充的数据
        :return: 解除填充后的数据
        """
        padding_length = padded_data[-1]
        if padding_length < 1 or padding_length > 16:
            raise ValueError("Invalid padding")
        for i in range(padding_length):
            if padded_data[-(i+1)] != padding_length:
                raise ValueError("Invalid padding")
        return padded_data[:-padding_length]
    
    def hkdf(self, input_key: bytes, length: int, salt: bytes = None, info: bytes = None) -> bytes:
        """
        使用HKDF进行密钥派生。
        :param input_key: 输入密钥
        :param length: 派生密钥长度
        :param salt: 盐
        :param info: 附加信息
        :return: 派生密钥
        """
        if salt is None:
            salt = bytes([0] * 32)
        if info is None:
            info = b""
            
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            info=info,
            backend=self.backend
        )
        return hkdf.derive(input_key)
    
    def constant_time_compare(self, a: bytes, b: bytes) -> bool:
        """
        比较两个字节串是否相等，使用常量时间。
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
    
    def encrypt_aes_gcm(self, key: bytes, data: bytes) -> tuple[bytes, bytes, bytes]:
        """
        使用AES-GCM进行认证加密
        :param key: 密钥
        :param data: 待加密数据
        :return: 加密后的密文、认证标签和随机数
        """
        if len(key) not in (16, 24, 32):
            raise ValueError("Invalid key length")
            
        nonce = self.get_random_bytes(12)
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return ciphertext, encryptor.tag, nonce
    
    def decrypt_aes_gcm(self, key: bytes, data: bytes, tag: bytes, nonce: bytes) -> bytes:
        """
        使用AES-GCM进行认证解密
        :param key: 密钥
        :param data: 密文
        :param tag: 认证标签
        :param nonce: 随机数
        :return: 解密后的明文
        """
        if len(key) not in (16, 24, 32):
            raise ValueError("Invalid key length")
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=self.backend)
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()
    
    def derive_key_pair(self, seed: bytes) -> tuple[bytes, bytes]:
        """
        从种子派生Ed25519密钥对。
        :param seed: 种子
        :return: Ed25519私钥和公钥
        """
        if len(seed) < 32:
            raise ValueError("Seed too short")
        priv = self.hkdf(seed, 32, info=b"key_derive")
        priv_key = x25519.X25519PrivateKey.from_private_bytes(priv)
        pub_key = priv_key.public_key()
        return priv, pub_key.public_bytes()