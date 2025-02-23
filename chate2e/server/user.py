from typing import Optional, List
from chate2e.model.bundle import Bundle
from chate2e.model.message import Message

class User:
    def __init__(self, username: str, uuid: str):
        self.username = username
        self.uuid = uuid
        self.bundle: Optional[Bundle] = None
        self.used_pre_keys: set = set()
        self.offline_messages: List[Message] = []
        self.is_online: bool = False
    
    def to_dict(self) -> dict:
        return {
            'username': self.username,
            'uuid': self.uuid,
            'bundle': self.bundle.to_dict() if self.bundle else None,
            'is_online': self.is_online
        }
        
    def set_bundle(self, bundle: Bundle) -> None:
        """设置用户的密钥Bundle"""
        self.bundle = bundle
        self.used_pre_keys.clear()

    def get_bundle(self) -> Optional[Bundle]:
        """获取用户的密钥Bundle"""
        return self.bundle

    def add_offline_message(self, message: Message) -> None:
        """添加离线消息"""
        self.offline_messages.append(message)

    def get_and_clear_offline_messages(self) -> List[dict]:
        """获取并清空离线消息"""
        messages = [msg.to_dict() for msg in self.offline_messages]
        self.offline_messages.clear()
        return messages