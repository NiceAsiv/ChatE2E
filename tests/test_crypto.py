import unittest
from src.core.crypto import generate_key_pair, encrypt_message, decrypt_message

class TestCryptoFunctions(unittest.TestCase):

    def setUp(self):
        self.private_key, self.public_key = generate_key_pair()
        self.message = "Hello, World!"
        self.encrypted_message = encrypt_message(self.message, self.public_key)

    def test_encrypt_message(self):
        self.assertIsNotNone(self.encrypted_message)
        self.assertNotEqual(self.encrypted_message, self.message)

    def test_decrypt_message(self):
        decrypted_message = decrypt_message(self.encrypted_message, self.private_key)
        self.assertEqual(decrypted_message, self.message)

if __name__ == '__main__':
    unittest.main()