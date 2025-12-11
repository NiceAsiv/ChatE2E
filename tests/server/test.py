import pytest
from unittest.mock import MagicMock, patch
from chate2e.server.chat_server import ChatServer
from chate2e.model.message import Message, MessageType
from chate2e.server.user import User


@pytest.fixture
def chat_server():
    server = ChatServer()
    server.socketio = MagicMock()
    return server


@pytest.fixture
def test_users():
    sender = User("sender", "sender123")
    receiver = User("receiver", "receiver456")
    return sender, receiver


@pytest.fixture
def test_message(test_users):
    sender, receiver = test_users
    return Message(
        message_id="msg123",
        sender_id=sender.uuid,
        session_id="session123",
        receiver_id=receiver.uuid,
        encrypted_content=b"test content",
        message_type=MessageType.MESSAGE
    )


class TestMessageForwarding:
    def test_forward_to_online_user(self, chat_server, test_users, test_message):
        """Test forwarding message to an online user"""
        sender, receiver = test_users
        socket_id = "socket789"

        # Setup test environment
        chat_server.users[receiver.uuid] = receiver
        chat_server.socket_sessions[receiver.uuid] = socket_id

        # Test forwarding
        result = chat_server.forward_message(test_message)

        # Verify results
        assert result is True
        chat_server.socketio.emit.assert_called_once_with(
            'message',
            test_message.to_dict(),
            room=socket_id
        )

    def test_forward_to_offline_user(self, chat_server, test_users, test_message):
        """Test handling message for offline user"""
        sender, receiver = test_users

        # Setup test environment
        chat_server.users[receiver.uuid] = receiver

        # Test forwarding
        result = chat_server.forward_message(test_message)

        # Verify results
        assert result is False
        assert test_message in chat_server.users[receiver.uuid].offline_messages

    @pytest.mark.asyncio
    async def test_socket_event_handler(self, test_message):
        """Test socket event handler for new messages"""
        from chate2e.server.app import handle_new_message

        # Setup mock request context
        with patch('flask_socketio.emit') as mock_emit:
            # Test handler
            response = handle_new_message(test_message.to_dict())

            # Verify results
            assert response['status'] == 'success'
            mock_emit.assert_called_once_with(
                'message',
                test_message.to_dict(),
                room=None
            )

    def test_forward_with_exception(self, chat_server, test_users, test_message):
        """Test message forwarding with exception handling"""
        sender, receiver = test_users
        socket_id = "socket789"

        # Setup test environment
        chat_server.users[receiver.uuid] = receiver
        chat_server.socket_sessions[receiver.uuid] = socket_id
        chat_server.socketio.emit.side_effect = Exception("Test error")

        # Test forwarding
        result = chat_server.forward_message(test_message)

        # Verify results
        assert result is False
        assert test_message in chat_server.users[receiver.uuid].offline_messages