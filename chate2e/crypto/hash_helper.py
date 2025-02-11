from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

class HashHelper:
    def __init__(self):
        self.backend = default_backend()

    @staticmethod
    def hash_sha256(self, data: bytes) -> bytes:
        """
        计算 SHA-256 摘要。
        :param data: 输入数据
        :return: SHA-256 哈希值
        """
        digest = hashes.Hash(hashes.SHA256(), backend=self.backend)
        digest.update(data)
        return digest.finalize()
    
    @staticmethod
    def hash_sha512(self, data: bytes) -> bytes:
        """
        计算SHA-512摘要。
        :param data: 输入数据
        :return: SHA-512哈希值
        """
        digest = hashes.Hash(hashes.SHA512(), backend=default_backend())
        digest.update(data)
        return digest.finalize()