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
from chate2e.utils.message import Message, MessageType, Encryption

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
            tag="test_tag"
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