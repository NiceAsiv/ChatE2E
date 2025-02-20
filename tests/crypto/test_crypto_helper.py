import pytest
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from chate2e.crypto.crypto_helper import CryptoHelper

@pytest.fixture
def crypto_helper():
    return CryptoHelper()

def test_get_random_bytes(crypto_helper):
    size = 16
    random_bytes = crypto_helper.get_random_bytes(size)
    assert len(random_bytes) == size

def test_encrypt_decrypt_aes_cbc(crypto_helper):
    key = crypto_helper.get_random_bytes(32)
    iv = crypto_helper.get_random_bytes(16)
    data = b"Test data for AES CBC mode"
    
    encrypted_data = crypto_helper.encrypt_aes_cbc(key, data, iv)
    decrypted_data = crypto_helper.decrypt_aes_cbc(key, encrypted_data, iv)
    
    assert decrypted_data == data

def test_encrypt_decrypt_aes_gcm(crypto_helper):
    key = crypto_helper.get_random_bytes(32)
    iv = crypto_helper.get_random_bytes(12)
    data = b"Test data for AES GCM mode"
    
    encrypted_data, tag = crypto_helper.encrypt_aes_gcm(key, data, iv)
    ciphertext = encrypted_data
    
    decrypted_data = crypto_helper.decrypt_aes_gcm(key, ciphertext, iv, tag)
    
    assert decrypted_data == data

def test_create_x25519_keypair(crypto_helper):
    private_key, public_key = crypto_helper.create_x25519_keypair()
    assert isinstance(private_key, x25519.X25519PrivateKey)
    assert isinstance(public_key, x25519.X25519PublicKey)

def test_ecdh(crypto_helper):
    priv_key1, pub_key1 = crypto_helper.create_x25519_keypair()
    priv_key2, pub_key2 = crypto_helper.create_x25519_keypair()
    
    shared_key1 = crypto_helper.ecdh(priv_key1, pub_key2)
    shared_key2 = crypto_helper.ecdh(priv_key2, pub_key1)
    
    assert shared_key1 == shared_key2

def test_export_x25519_public_key(crypto_helper):
    private_key, _ = crypto_helper.create_x25519_keypair()
    public_key_bytes = crypto_helper.export_x25519_public_key(private_key)
    
    assert isinstance(public_key_bytes, bytes)
    assert len(public_key_bytes) == 32

def test_generate_ed25519_keypair(crypto_helper):
    private_key, public_key = crypto_helper.generate_ed25519_keypair()
    assert isinstance(private_key, ed25519.Ed25519PrivateKey)
    assert isinstance(public_key, ed25519.Ed25519PublicKey)

def test_export_ed25519_public_key(crypto_helper):
    private_key, _ = crypto_helper.generate_ed25519_keypair()
    public_key_bytes = crypto_helper.export_ed25519_public_key(private_key)
    
    assert isinstance(public_key_bytes, bytes)
    assert len(public_key_bytes) == 32

def test_hkdf(crypto_helper):
    input_key = crypto_helper.get_random_bytes(32)
    length = 32
    derived_key = crypto_helper.hkdf(input_key, length)
    
    assert len(derived_key) == length