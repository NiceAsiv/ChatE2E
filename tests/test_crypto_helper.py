import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519, ed25519
from chate2e.crypto.crypto_helper import CryptoHelper

@pytest.fixture
def crypto_helper():
    """Fixture for setting up CryptoHelper instance."""
    return CryptoHelper()

@pytest.fixture
def test_data():
    """Fixture for test data."""
    return {
        'key': b'\x00' * 32,
        'data': b'hello world' + b'\x00' * 5,  # 确保数据长度是块长度的倍数
        'iv': b'\x00' * 16
    }

def test_sign_hmac(crypto_helper, test_data):
    mac = crypto_helper.sign_hmac(test_data['key'], test_data['data'])
    assert len(mac) == 32

def test_get_random_bytes(crypto_helper):
    random_bytes = crypto_helper.get_random_bytes(16)
    assert len(random_bytes) == 16

def test_encrypt_decrypt_aes_cbc(crypto_helper, test_data):
    encrypted = crypto_helper.encrypt_aes_cbc(test_data['key'], test_data['data'], test_data['iv'])
    decrypted = crypto_helper.decrypt_aes_cbc(test_data['key'], encrypted, test_data['iv'])
    assert decrypted == test_data['data']

def test_hash_sha512(crypto_helper, test_data):
    hash_value = crypto_helper.hash_sha512(test_data['data'])
    assert len(hash_value) == 64

def test_kdf(crypto_helper):
    salt = b'\x00' * 32
    info = b'info'
    derived_keys = crypto_helper.kdf(b'hello world', salt, info)
    assert len(derived_keys) == 2
    assert len(derived_keys[0]) == 32
    assert len(derived_keys[1]) == 32

def test_create_key_pair(crypto_helper):
    key_pair = crypto_helper.create_key_pair()
    assert isinstance(key_pair, x25519.X25519PrivateKey)

def test_ecdhe(crypto_helper):
    priv_key = crypto_helper.create_key_pair()
    pub_key_bytes = priv_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    shared_key = crypto_helper.ecdhe(pub_key_bytes, priv_key)
    assert len(shared_key) == 32

def test_ed25519_sign_verify(crypto_helper):
    priv_key = ed25519.Ed25519PrivateKey.generate()
    priv_key_bytes = priv_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption()
    )
    pub_key_bytes = priv_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    message = b'message'
    signature = crypto_helper.ed25519_sign(priv_key_bytes, message)
    assert crypto_helper.ed25519_verify(pub_key_bytes, message, signature)

def test_verify_mac(crypto_helper, test_data):
    mac = crypto_helper.sign_hmac(test_data['key'], test_data['data'])
    crypto_helper.verify_mac(test_data['data'], test_data['key'], mac, len(mac))