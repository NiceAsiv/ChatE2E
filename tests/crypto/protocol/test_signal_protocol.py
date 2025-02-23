import pytest
import asyncio
import uuid

from chate2e.crypto.protocol.signal_protocol import SignalProtocol
from chate2e.model.message import Message, MessageType
from chate2e.model.bundle import Bundle

@pytest.fixture
def alice():
    protocol = SignalProtocol()
    protocol.initialize_identity("alice")
    return protocol

@pytest.fixture
def bob():
    protocol = SignalProtocol()
    protocol.initialize_identity("bob")
    return protocol

@pytest.fixture
def session_id():
    return uuid.uuid4().hex[:16]

class TestSignalProtocol:
    
    def test_initialize_identity(self, alice):
        """测试身份初始化"""
        assert alice.user_id == "alice"
        assert alice.identity_key is not None
        assert alice.identity_key_pub is not None
        assert alice.signed_prekey is not None
        assert alice.signed_prekey_pub is not None
        assert len(alice.one_time_prekeys) == alice.MAX_ONE_TIME_PREKEYS
        assert len(alice.one_time_prekeys_pub) == alice.MAX_ONE_TIME_PREKEYS

    def test_create_bundle(self, alice):
        """测试创建密钥束"""
        bundle = alice.create_bundle()
        assert isinstance(bundle, Bundle)
        assert bundle.identity_key_pub is not None
        assert bundle.signed_pre_key_pub is not None
        assert bundle.signed_pre_key_signature is not None
        assert len(bundle.one_time_pre_keys_pub) == alice.MAX_ONE_TIME_PREKEYS

    def test_create_and_load_local_bundle(self, alice):
        """测试创建和加载本地密钥束"""
        local_bundle = alice.create_local_bundle()
        
        # 创建新的协议实例并加载bundle
        new_alice = SignalProtocol()
        new_alice.load_signal_from_local_bundle(local_bundle)
        
        # 验证密钥是否正确加载
        assert new_alice.identity_key is not None
        assert new_alice.identity_key_pub is not None
        assert new_alice.signed_prekey is not None
        assert new_alice.signed_prekey_pub is not None
        assert len(new_alice.one_time_prekeys) == alice.MAX_ONE_TIME_PREKEYS
        assert len(new_alice.one_time_prekeys_pub) == alice.MAX_ONE_TIME_PREKEYS

    def test_session_initialization(self, alice, bob, session_id):
        """测试会话初始化"""
        # 交换密钥束
        alice_bundle = alice.create_bundle()
        bob_bundle = bob.create_bundle()
        
        alice.set_peer_bundle("bob", bob_bundle)
        bob.set_peer_bundle("alice", alice_bundle)

        # Alice初始化会话
        init_message = alice.initiate_session(
            peer_id="bob",
            session_id=session_id,
            recipient_identity_key=bob.identity_key_pub,
            recipient_signed_prekey=bob.signed_prekey_pub,
            recipient_one_time_prekey=bob.one_time_prekeys_pub[0],
            is_initiator=True
        )
        
        # Bob处理初始化消息
        bob_response = bob.initiate_session(
            peer_id="alice",
            session_id=session_id,
            recipient_identity_key=alice.identity_key_pub,
            recipient_signed_prekey=alice.signed_prekey_pub,
            recipient_ephemeral_key=alice.ephemeral_key_pub,
            own_one_time_prekey=bob.one_time_prekeys_pub[0],
            is_initiator=False
        )

        # 验证会话状态
        assert alice.session_initialized
        assert bob.session_initialized
        assert alice.is_initiator
        assert not bob.is_initiator
        assert alice.session_id == session_id
        assert bob.session_id == session_id

    def test_message_exchange(self, alice, bob, session_id):
        """测试消息交换"""
        # 初始化会话
        alice_bundle = alice.create_bundle()
        bob_bundle = bob.create_bundle()
        
        alice.set_peer_bundle("bob", bob_bundle)
        bob.set_peer_bundle("alice", alice_bundle)

        alice.initiate_session(
            peer_id="bob",
            session_id=session_id,
            recipient_identity_key=bob.identity_key_pub,
            recipient_signed_prekey=bob.signed_prekey_pub,
            recipient_one_time_prekey=bob.one_time_prekeys_pub[0],
            is_initiator=True
        )
        
        bob.initiate_session(
            peer_id="alice",
            session_id=session_id,
            recipient_identity_key=alice.identity_key_pub,
            recipient_signed_prekey=alice.signed_prekey_pub,
            recipient_ephemeral_key=alice.ephemeral_key_pub,
            own_one_time_prekey=bob.one_time_prekeys_pub[0],
            is_initiator=False
        )

        # 测试消息交换
        messages = [
            "Message 1 from Alice",
            "Message 2 from Bob",
            "Message 3 from Alice"
        ]

        # Alice -> Bob
        encrypted1 = alice.encrypt_message(messages[0])
        decrypted1 = bob.decrypt_message(encrypted1)
        assert decrypted1 == messages[0]

        # Bob -> Alice
        encrypted2 = bob.encrypt_message(messages[1])
        decrypted2 = alice.decrypt_message(encrypted2)
        assert decrypted2 == messages[1]

        # Alice -> Bob
        encrypted3 = alice.encrypt_message(messages[2])
        decrypted3 = bob.decrypt_message(encrypted3)
        assert decrypted3 == messages[2]

    def test_error_handling(self, alice):
        """测试错误处理"""
        # 测试未初始化会话的错误
        with pytest.raises(Exception, match="Session not initialized"):
            alice.encrypt_message("Test message")

        # 测试缺少必要参数的错误
        with pytest.raises(ValueError):
            alice.initiate_session(
                peer_id="bob",
                session_id="test",
                recipient_identity_key=None,
                recipient_signed_prekey=None,
                is_initiator=False
            )