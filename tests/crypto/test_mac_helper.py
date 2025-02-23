import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from chate2e.crypto.mac_helper import MACHelper

def test_hmac_sign_verify():
    key = b"asdaawqeasdasd"
    data = b"test-data"

    # 测试签名
    mac = MACHelper.sign(data, key)
    assert isinstance(mac, bytes)
    assert len(mac) == 32  # SHA256 输出长度

    # 测试成功验证
    MACHelper.verify(key, data, mac)  # 不应抛出异常

    # 测试失败验证 - 错误的密钥
    wrong_key = b"wrong-key"
    with pytest.raises(ValueError, match="Bad MAC"):
        MACHelper.verify(wrong_key, data, mac)

    # 测试失败验证 - 错误的数据
    wrong_data = b"wrong-data"
    with pytest.raises(ValueError, match="Bad MAC"):
        MACHelper.verify(key, wrong_data, mac)

    # 测试失败验证 - 错误的 MAC
    wrong_mac = b"x" * 32
    with pytest.raises(ValueError, match="Bad MAC"):
        MACHelper.verify(key, data, wrong_mac)

def test_constant_time_compare():
    a = b"test"
    b = b"test"
    c = b"different"
    
    assert MACHelper.constant_time_compare(a, b) is True
    assert MACHelper.constant_time_compare(a, c) is False
    assert MACHelper.constant_time_compare(a, b"tes") is False

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from chate2e.crypto.mac_helper import MACHelper

def test_ed25519_sign_verify():
    # 生成测试密钥对
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    # 获取私钥字节
    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # 获取公钥字节
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    # 测试消息
    message = b"Test message for Ed25519"
    
    # 使用MACHelper进行签名
    signature = MACHelper.ed25519_sign(priv_bytes, message)
    
    # 验证签名
    assert MACHelper.ed25519_verify(pub_bytes, message, signature)
    
    # 验证错误的消息
    wrong_message = b"Wrong message"
    assert not MACHelper.ed25519_verify(pub_bytes, wrong_message, signature)