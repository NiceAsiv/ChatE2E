import pytest
from chate2e.crypto.crypto_helper import CryptoHelper
from cryptography.hazmat.primitives import serialization

@pytest.fixture
def crypto_helper():
    """Fixture for setting up CryptoHelper instance."""
    return CryptoHelper()

def test_e2e_encryption(crypto_helper):
    """
    端到端加密测试，包含密钥交换、加密通信。
    """
    crypto = crypto_helper

    # 1. Alice 和 Bob 各自生成 X25519 密钥对
    alice_priv, alice_pub = crypto.create_x25519_keypair()
    bob_priv, bob_pub = crypto.create_x25519_keypair()

    # 导出公钥字节，注意使用公钥而不是私钥
    alice_pub_bytes = crypto.export_x25519_public_key(alice_pub)
    bob_pub_bytes = crypto.export_x25519_public_key(bob_pub)

    # 2. Alice 使用 Bob 的公钥和自己的私钥生成共享密钥
    shared_key_alice = crypto.ecdh(alice_priv, bob_pub)  # 直接使用公钥对象
    # 3. Bob 使用 Alice 的公钥和自己的私钥生成共享密钥
    shared_key_bob = crypto.ecdh(bob_priv, alice_pub)  # 直接使用公钥对象
    
    assert shared_key_alice == shared_key_bob

    # 4. 双方使用共享密钥的前 32 字节作为 AES 密钥，前 16 字节做 IV
    aes_key = shared_key_alice[:32]
    iv = shared_key_alice[:16]

    # 5. Alice 加密信息
    message = b"Hello, this is a secret message."
    ciphertext, tag = crypto.encrypt_aes_gcm(aes_key, message, iv)
    print("密文:", ciphertext.hex())
    print("认证标签:", tag.hex())
    
    # 6. Bob 解密信息
    decrypted = crypto.decrypt_aes_gcm(aes_key, ciphertext, iv, tag)
    print("解密后:", decrypted.decode())
    
    assert decrypted == message