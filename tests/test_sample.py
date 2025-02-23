import pytest
from chate2e.sample import SignalProtocol, EncryptedMessage
import base64

@pytest.fixture
async def alice_bob():
    """创建并初始化 Alice 和 Bob 的协议实例"""
    alice = SignalProtocol()
    bob = SignalProtocol()
    
    # 生成密钥
    alice.generate_identity_key()
    bob.generate_identity_key()
    alice.generate_signed_prekey() 
    bob.generate_signed_prekey()
    
    # 生成一次性预密钥
    alice_otk_id = alice.generate_one_time_prekey()
    bob_otk_id = bob.generate_one_time_prekey()
    
    # 初始化会话
    shared_secret = await alice.initiate_session(
        bob.identity_key_pub,
        bob.signed_prekey_pub,
        recipient_one_time_prekey=bob.one_time_prekeys[bob_otk_id][1],
        is_initiator=True
    )
    
    await bob.initiate_session(
        alice.identity_key_pub,
        alice.signed_prekey_pub,
        recipient_ephemeral_key=alice.ephemeral_key_pub,
        own_one_time_prekey=bob.one_time_prekeys[bob_otk_id][1],
        is_initiator=False
    )
    
    return alice, bob

@pytest.mark.asyncio
async def test_key_generation():
    """Test key generation functions"""
    protocol = SignalProtocol()
    
    # Test identity key generation
    protocol.generate_identity_key()
    assert protocol.identity_key is not None
    assert protocol.identity_key_pub is not None
    
    # Test signed prekey generation
    protocol.generate_signed_prekey()
    assert protocol.signed_prekey is not None
    assert protocol.signed_prekey_pub is not None
    
    # Test one-time prekey generation
    key_id = protocol.generate_one_time_prekey()
    assert key_id == 0
    assert len(protocol.one_time_prekeys) == 1
    assert protocol.one_time_prekeys[0][0] is not None  # private key
    assert protocol.one_time_prekeys[0][1] is not None  # public key

@pytest.mark.asyncio
async def test_session_initialization(alice_bob):
    """测试会话初始化"""
    alice, bob = await alice_bob
    
    # 验证两个会话都已初始化
    assert alice.session_initialized
    assert bob.session_initialized
    
    # 验证发起者/响应者角色
    assert alice.is_initiator
    assert not bob.is_initiator
    
    # 验证密钥已设置
    assert alice.root_key is not None
    assert alice.sending_chain_key is not None
    assert alice.receiving_chain_key is not None
    assert bob.root_key is not None
    assert bob.sending_chain_key is not None
    assert bob.receiving_chain_key is not None

@pytest.mark.asyncio
async def test_message_encryption_decryption(alice_bob):
    """测试消息加密和解密"""
    alice, bob = await alice_bob
    
    # 测试 Alice -> Bob 消息
    message = "Hello Bob!"
    encrypted = await alice.encrypt_message(message)
    
    assert isinstance(encrypted, EncryptedMessage)
    assert encrypted.ciphertext is not None
    assert 'nonce' in encrypted.header
    assert 'is_initiator' in encrypted.header
    
    decrypted = await bob.decrypt_message(encrypted)
    assert decrypted == message
    
    # 测试 Bob -> Alice 消息
    message = "Hello Alice!"
    encrypted = await bob.encrypt_message(message)
    decrypted = await alice.decrypt_message(encrypted)
    assert decrypted == message

@pytest.mark.asyncio 
async def test_multiple_messages(alice_bob):
    """测试多条消息交换"""
    alice, bob = await alice_bob
    
    messages = [
        "Message 1",
        "Message 2", 
        "Message 3"
    ]
    
    # 测试多条 Alice -> Bob 消息
    for msg in messages:
        encrypted = await alice.encrypt_message(msg)
        decrypted = await bob.decrypt_message(encrypted)
        assert decrypted == msg
        
    # 测试多条 Bob -> Alice 消息
    for msg in messages:
        encrypted = await bob.encrypt_message(msg)
        decrypted = await alice.decrypt_message(encrypted)
        assert decrypted == msg

@pytest.mark.asyncio
async def test_error_cases():
    """Test error cases"""
    protocol = SignalProtocol()
    
    # Test encryption without initialized session
    with pytest.raises(Exception, match="Session not initialized"):
        await protocol.encrypt_message("test")
        
    # Test decryption without initialized session
    with pytest.raises(Exception, match="Session not initialized"):
        await protocol.decrypt_message(
            EncryptedMessage(b"test", {'nonce': 'test', 'is_initiator': True})
        )
        
    # Test responder init without ephemeral key
    with pytest.raises(ValueError, match="响应方初始化时必须提供发起方的临时公钥"):
        await protocol.initiate_session(
            None, None,
            recipient_ephemeral_key=None,
            is_initiator=False
        )