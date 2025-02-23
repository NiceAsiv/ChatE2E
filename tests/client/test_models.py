# tests/client/test_models.py
import pytest
import os
import uuid
from datetime import datetime, timezone
from chate2e.client.models import (
    UserStatus,
    Friend,
    UserProfile,
    ChatSession,
    DataManager
)
from chate2e.model.message import Message, MessageType, Encryption
from chate2e.model.bundle import Bundle

# Fixtures
@pytest.fixture
def test_dir():
    dir_name = "test_chat_data"
    yield dir_name
    # 清理测试目录
    if os.path.exists(dir_name):
        for root, dirs, files in os.walk(dir_name, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(dir_name)

@pytest.fixture
def test_user():
    return UserProfile(
        user_id="test001",
        username="TestUser",
        avatar_path="assets/avatars/test.png",
        status=UserStatus.ONLINE
    )

@pytest.fixture
def test_friend():
    return Friend(
        user_id="friend001",
        username="TestFriend",
        avatar_path="assets/avatars/friend.png",
        status=UserStatus.OFFLINE
    )

@pytest.fixture
def test_session(test_user, test_friend):
    return ChatSession(
        participant1_id=test_user.user_id,
        participant2_id=test_friend.user_id
    )

@pytest.fixture
def data_manager(test_dir):
    return DataManager("test001", test_dir)

# UserStatus Tests
def test_user_status_conversion():
    assert UserStatus.from_str("online") == UserStatus.ONLINE
    assert UserStatus.from_str("OFFLINE") == UserStatus.OFFLINE
    assert UserStatus.from_str("invalid") == UserStatus.OFFLINE

# Friend Tests
def test_friend_creation_and_conversion(test_friend):
    # 测试创建
    assert test_friend.user_id == "friend001"
    assert test_friend.status == UserStatus.OFFLINE
    
    # 测试转换
    friend_dict = test_friend.to_dict()
    restored_friend = Friend.from_dict(friend_dict)
    assert restored_friend.user_id == test_friend.user_id
    assert restored_friend.status == test_friend.status

# UserProfile Tests
def test_user_profile_management(test_user, test_friend):
    # 测试添加好友
    assert test_user.add_friend(test_friend) == True
    assert len(test_user.friends) == 1
    
    # 测试重复添加
    assert test_user.add_friend(test_friend) == False
    assert len(test_user.friends) == 1
    
    # 测试获取好友
    found_friend = test_user.get_friend(test_friend.user_id)
    assert found_friend.user_id == test_friend.user_id
    
    # 测试移除好友
    assert test_user.remove_friend(test_friend.user_id) == True
    assert len(test_user.friends) == 0

def test_user_profile_serialization(test_user, test_friend):
    test_user.add_friend(test_friend)
    user_dict = test_user.to_dict()
    restored_user = UserProfile.from_dict(user_dict)
    
    assert restored_user.user_id == test_user.user_id
    assert restored_user.username == test_user.username
    assert restored_user.status == test_user.status
    assert len(restored_user.friends) == len(test_user.friends)

# ChatSession Tests
def test_chat_session_management(test_session):
    # 测试会话创建
    assert test_session.session_id is not None
    assert len(test_session.messages) == 0
    
    # 测试消息添加
    message = Message(
        message_id=str(uuid.uuid4()),
        session_id=test_session.session_id,
        sender_id=test_session.participant1_id,
        receiver_id=test_session.participant2_id,
        encrypted_content="Test message",
        message_type=MessageType.MESSAGE,
        encryption=Encryption(
            algorithm="AES-GCM",
            iv="test_iv",
            tag="test_tag",
            is_initiator=True
        )
    )
    test_session.add_message(message)
    assert len(test_session.messages) == 1
    assert test_session.last_message == message

def test_chat_session_serialization(test_session):
    session_dict = test_session.to_dict()
    restored_session = ChatSession.from_dict(session_dict)
    
    assert restored_session.session_id == test_session.session_id
    assert restored_session.participant1_id == test_session.participant1_id
    assert restored_session.participant2_id == test_session.participant2_id

# DataManager Tests
def test_data_manager_user_operations(data_manager, test_user):
    # 测试设置用户
    data_manager.set_user(test_user)
    assert data_manager.user.user_id == test_user.user_id
    
    # 测试保存和加载
    data_manager.save_data()
    data_manager.load_data()
    assert data_manager.user.user_id == test_user.user_id

def test_data_manager_session_operations(data_manager, test_user, test_friend):
    data_manager.set_user(test_user)
    
    # 测试创建会话
    session = data_manager.get_or_create_session(test_friend.user_id)
    assert session.session_id in data_manager.sessions
    
    # 测试添加消息
    message = Message(
        message_id=str(uuid.uuid4()),
        session_id=session.session_id,
        sender_id=test_user.user_id,
        receiver_id=test_friend.user_id,
        encrypted_content="Test message",
        message_type=MessageType.MESSAGE,
        encryption=None
    )
    data_manager.add_message(session.session_id, message)
    assert len(data_manager.sessions[session.session_id].messages) == 1

    def test_user_password_management(test_user):
        # Test password setting and verification
        test_user.set_password("testpass123")
        assert test_user.password_hash is not None
        assert test_user.salt is not None
        assert test_user.verify_password("testpass123") == True
        assert test_user.verify_password("wrongpass") == False

    def test_chat_session_participant_management(test_session):
        # Test participant management
        assert test_session.has_participant(test_session.participant1_id) == True
        assert test_session.has_participant("nonexistent") == False
        
        # Test getting other participant
        other = test_session.get_other_participant(test_session.participant1_id)
        assert other == test_session.participant2_id
        
        # Test invalid participant
        assert test_session.get_other_participant("nonexistent") is None

    def test_data_manager_user_registration(data_manager, test_dir):
        # Test user registration
        test_bundle = Bundle(
            identity_key="test_identity",
            signed_pre_key="test_prekey",
            one_time_pre_keys=["test_onetime"]
        )
        
        success = data_manager.register_user(
            username="newuser",
            password="password123",
            user_uuid="test002",
            bundle=test_bundle
        )
        assert success == True
        assert os.path.exists(os.path.join(test_dir, "test002", "user_profile.json"))

    def test_data_manager_user_verification(data_manager, test_dir):
        # Register a test user first
        test_bundle = Bundle(
            identity_key="test_identity",
            signed_pre_key="test_prekey",
            one_time_pre_keys=["test_onetime"]
        )
        data_manager.register_user("testuser", "testpass", "test003", test_bundle)
        
        # Test verification
        user_id = data_manager.verify_user("testuser", "testpass")
        assert user_id == "test003"
        
        # Test wrong password
        assert data_manager.verify_user("testuser", "wrongpass") is None
        
        # Test nonexistent user
        assert data_manager.verify_user("nonexistent", "anypass") is None

    def test_chat_session_sorting(test_session):
        # Test participant ID sorting
        session = ChatSession(
            participant1_id="user2",
            participant2_id="user1"
        )
        assert session.participant1_id == "user1"
        assert session.participant2_id == "user2"

    def test_data_manager_last_message(data_manager, test_user, test_friend):
        data_manager.set_user(test_user)
        session = data_manager.get_or_create_session(test_friend.user_id)
        
        # Test when no messages exist
        assert data_manager.get_last_message(test_friend.user_id) is None
        
        # Add a message and test
        message = Message(
            message_id=str(uuid.uuid4()),
            session_id=session.session_id,
            sender_id=test_user.user_id,
            receiver_id=test_friend.user_id,
            encrypted_content="Test message",
            message_type=MessageType.MESSAGE,
            encryption=None
        )
        data_manager.add_message(session.session_id, message)
        
        last_message = data_manager.get_last_message(test_friend.user_id)
        assert last_message == message

import pytest
from datetime import datetime, timezone
from chate2e.client.models import UserProfile, UserStatus, Friend
from chate2e.model.bundle import Bundle
import os

@pytest.fixture
def test_bundle():
    """创建测试用的Bundle对象"""
    return Bundle(
        identity_key_pub=b'test_identity_key',
        signed_pre_key_pub=b'test_signed_pre_key',
        signed_pre_key_signature=b'test_signature',
        one_time_pre_keys_pub=frozenset([b'test_one_time_key'])
    )

@pytest.fixture
def test_user_profile(test_bundle):
    """创建测试用的UserProfile对象"""
    user = UserProfile(
        user_id="test001",
        username="测试用户",
        avatar_path="assets\\avatars\default.png",
        status=UserStatus.ONLINE,
        last_seen=datetime.now(timezone.utc)
    )
    user.set_password("test_password")
    user.set_bundle(test_bundle)
    return user

def test_user_profile_basic_serialization(test_user_profile):
    """测试基本信息的序列化"""
    user_dict = test_user_profile.to_dict()
    
    # 验证基本字段
    expected_path = os.path.join("assets", "avatars", "default.png")
    assert user_dict['user_id'] == "test001"
    assert user_dict['username'] == "测试用户"
    # assert user_dict['avatar_path'] == expected_path
    assert user_dict['status'] == "online"
    assert 'last_seen' in user_dict
    
    # 从字典恢复对象
    restored_user = UserProfile.from_dict(user_dict)
    assert restored_user.user_id == test_user_profile.user_id
    assert restored_user.username == test_user_profile.username
    assert restored_user.status == test_user_profile.status

def test_user_profile_password_serialization(test_user_profile):
    """测试密码相关信息的序列化"""
    user_dict = test_user_profile.to_dict()
    
    # 验证密码相关字段
    assert 'password_hash' in user_dict
    assert 'salt' in user_dict
    assert user_dict['password_hash'] is not None
    assert user_dict['salt'] is not None
    
    # 从字典恢复对象并验证密码
    restored_user = UserProfile.from_dict(user_dict)
    assert restored_user.verify_password("test_password")

def test_user_profile_friends_serialization(test_user_profile):
    """测试好友列表的序列化"""
    # 添加测试好友
    friend = Friend(
        user_id="friend001",
        username="测试好友",
        avatar_path="assets/avatars/default.png",
        status=UserStatus.OFFLINE
    )
    test_user_profile.add_friend(friend)
    
    user_dict = test_user_profile.to_dict()
    
    # 验证好友列表
    assert 'friends' in user_dict
    assert len(user_dict['friends']) == 1
    assert user_dict['friends'][0]['user_id'] == "friend001"
    
    # 从字典恢复对象
    restored_user = UserProfile.from_dict(user_dict)
    assert len(restored_user.friends) == 1
    assert restored_user.friends[0].user_id == "friend001"
    assert restored_user.friends[0].status == UserStatus.OFFLINE

def test_user_profile_bundle_serialization(test_user_profile, test_bundle):
    """测试Bundle的序列化"""
    user_dict = test_user_profile.to_dict()
    
    # 验证Bundle字段
    assert 'bundle' in user_dict
    assert user_dict['bundle'] is not None
    
    # 从字典恢复对象
    restored_user = UserProfile.from_dict(user_dict)
    restored_bundle = restored_user.get_bundle()
    
    # 验证Bundle内容
    assert restored_bundle is not None
    assert restored_bundle.identity_key_pub == test_bundle.identity_key_pub
    assert restored_bundle.signed_pre_key_pub == test_bundle.signed_pre_key_pub

def test_user_profile_complete_serialization(test_user_profile):
    """测试完整的序列化和反序列化过程"""
    # 序列化
    user_dict = test_user_profile.to_dict()
    
    # 验证所有必要字段
    required_fields = {
        'user_id', 'username', 'avatar_path', 'status', 
        'last_seen', 'password_hash', 'salt', 'bundle', 'friends'
    }
    assert all(field in user_dict for field in required_fields)
    
    # 反序列化
    restored_user = UserProfile.from_dict(user_dict)
    
    # 验证恢复后的对象
    assert restored_user.user_id == test_user_profile.user_id
    assert restored_user.username == test_user_profile.username
    assert restored_user.status == test_user_profile.status
    assert restored_user.verify_password("test_password")
    assert restored_user.get_bundle() is not None