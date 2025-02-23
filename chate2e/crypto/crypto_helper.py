import os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import padding
from typing import Tuple, Optional

class CryptoHelper:
    """
    加密辅助类，AES加解密、SHA-512哈希、KDF
    """
    def __init__(self):
        self.backend = default_backend()
        
    def get_random_bytes(self, size: int) -> bytes:
        """
        生成指定长度的随机字节。
        :param size: 随机字节长度
        :return: 生成的随机字节
        """
        return os.urandom(size)


    def encrypt_aes_cbc(self,key: bytes, data: bytes, iv: bytes) -> bytes:
        """
        使用AES-CBC模式进行加密。
        :param key: 原始密钥
        :param data: 待加密数据
        :param iv: 初始向量
        :return: 加密结果
        """
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(data) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(padded_data) + encryptor.finalize()
        
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
        padded_data = decryptor.update(data) + decryptor.finalize()
        
        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        return data
     
    def encrypt_aes_gcm(self, key: bytes, data: bytes, iv: bytes) -> Tuple[bytes, bytes]:
        """
        使用 AES-GCM 模式进行加密。
        :param key: 原始密钥
        :param data: 待加密数据
        :param iv: 初始向量（通常为12或16字节，需与解密时保持一致）
        :return: 加密结果 (密文 + 认证标签)
        """
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        return ciphertext , encryptor.tag
    
    def decrypt_aes_gcm(self, key: bytes, data: bytes, iv: bytes, tag: Optional[bytes]) -> bytes:
        """
        使用 AES-GCM 模式进行解密。
        :param key: 原始密钥
        :param data: 待解密数据（密文部分）
        :param iv: 初始向量（必须与加密时相同）
        :param tag: 认证标签 
        :return: 解密结果
        :raises ValueError: 如果认证标签验证失败
        """
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        try:
            return decryptor.update(data) + decryptor.finalize()
        except ValueError:
            raise ValueError("AES-GCM tag verification failed (decryption error).")
    
  
    def create_x25519_keypair(self, priv_key: bytes = None) -> Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]:
        """
        生成或使用给定的X25519密钥对,用于密钥交换。
        :param priv_key: 可选的32字节私钥
        :return: (私钥, 公钥)
        """
        if priv_key is None:
            private_key = x25519.X25519PrivateKey.generate()
        else:
            private_key = x25519.X25519PrivateKey.from_private_bytes(priv_key)
        public_key = private_key.public_key()
        return private_key, public_key
    
    def ecdh(self, priv_key: x25519.X25519PrivateKey, pub_key: x25519.X25519PublicKey) -> bytes:
        """
        执行X25519的DH密钥交换。
        :param priv_key: 本地X25519私钥
        :param pub_key: 对方的X25519公钥
        :return: 协商得出的共享密钥
        """
        if not isinstance(priv_key, x25519.X25519PrivateKey):
            raise TypeError("priv_key must be an instance of x25519.X25519PrivateKey, not %r" % priv_key)
        if isinstance(pub_key, bytes):
            pub_key = x25519.X25519PublicKey.from_public_bytes(pub_key)
        if not isinstance(pub_key, x25519.X25519PublicKey):
            raise TypeError("pub_key must be an instance of x25519.X25519PublicKey, not %r" % pub_key)
        return priv_key.exchange(pub_key)
    
    def export_x25519_public_key(self, public_key: x25519.X25519PublicKey) -> bytes:
        """
        导出 X25519 公钥的原始字节表示。
        :param public_key: X25519 公钥对象
        :return: 公钥字节
        """
        return public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
    def export_x25519_private_key(self, private_key: x25519.X25519PrivateKey) -> bytes:
        """
        导出 X25519 私钥的原始字节表示。
        :param private_key: X25519 私钥对象
        :return: 私钥字节
        """
        return private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def import_x25519_private_key(self, private_key: bytes) -> x25519.X25519PrivateKey:
        """
        导入 X25519 私钥。
        :param private_key: X25519 私钥字节
        :return: X25519 私钥对象
        """
        return x25519.X25519PrivateKey.from_private_bytes(private_key)
    
    def import_x25519_public_key(self, public_key: bytes) -> x25519.X25519PublicKey:
        """
        导入 X25519 公钥。
        :param public_key: X25519 公钥字节
        :return: X25519 公钥对象
        """
        return x25519.X25519PublicKey.from_public_bytes(public_key)    
            
    def export_ed25519_public_key(self,private_key: ed25519.Ed25519PrivateKey) -> bytes:
        """
        导出 Ed25519 公钥的原始字节表示。
        :param private_key: Ed25519 私钥对象
        :return: 公钥字节
        """
        public_key = private_key.public_key()
        return public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def generate_priv_x25519_keypair(self) -> x25519.X25519PrivateKey:
        """
        生成一次性或者临时X25519密钥对。
        :return: 私钥
        """
        return x25519.X25519PrivateKey.generate()

    def generate_ed25519_keypair(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """
        生成Ed25519密钥对。
        :return: (私钥, 公钥)
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        return private_key, public_key

    def hkdf(self, input_key: bytes, length: int, salt: bytes = None, info: bytes = None) -> bytes:
        """
        使用 HKDF(基于 HMAC 的密钥派生函数) 派生密钥。
        :param input_key: 输入密钥
        :param length: 派生密钥长度
        :param salt: 盐（可选，默认为32字节 0）
        :param info: 附加信息（可选，默认为空字节串）
        :return: 派生密钥
        """
        input_key = b'\xff' * 32 + input_key
        if salt is None:
            salt = b'\0'*32
        if info is None:
            info = b""
            
        hkdf_obj = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            info=info,
            backend=self.backend
        )
        return hkdf_obj.derive(input_key)