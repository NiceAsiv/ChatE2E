import unittest
from src.core.crypto import CryptoHelper
from cryptography.hazmat.primitives import serialization

class TestCryptoFunctions(unittest.TestCase):

    def setUp(self):
        self.crypto = CryptoHelper()

    def test_e2e_encryption(self):
        """
        端到端加密测试，包含密钥交换、加密通信。
        """
        crypto = self.crypto

        # 1. Alice 和 Bob 各自生成 X25519 密钥对
        alice_priv = crypto.create_key_pair()
        bob_priv = crypto.create_key_pair()

        alice_pub = alice_priv.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw
        )
        bob_pub = bob_priv.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw
        )

        # 2. Alice 使用 Bob 的公钥和自己的私钥生成共享密钥
        shared_key_alice = crypto.ecdhe(bob_pub, alice_priv)
        # 3. Bob 使用 Alice 的公钥和自己的私钥生成共享密钥
        shared_key_bob = crypto.ecdhe(alice_pub, bob_priv)
        
        self.assertEqual(shared_key_alice, shared_key_bob)

        # 4. 双方使用共享密钥的前 32 字节作为 AES 密钥，前 16 字节做 IV
        aes_key = shared_key_alice[:32]
        iv = shared_key_alice[:16]

        # 5. Alice 加密信息
        message = b"Hello, this is a secret message."
        ciphertext = crypto.encrypt_aes_cbc(aes_key, message, iv)
        print("Ciphertext:", ciphertext)

        # 6. Bob 解密信息
        decrypted = crypto.decrypt_aes_cbc(aes_key, ciphertext, iv)
        print("Decrypted:", decrypted)
        self.assertEqual(decrypted, message)

if __name__ == "__main__":
    unittest.main()