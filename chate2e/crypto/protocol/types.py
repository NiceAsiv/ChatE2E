from __future__ import annotations

import enum
from typing import FrozenSet, List, Mapping, NamedTuple, Optional, Union
from base64 import b64encode, b64decode

class Bundle(NamedTuple):
    """
    这个Bundle类用于存储X3DH协议中的密钥信息和signature。
    """
    identity_key: bytes
    signed_pre_key: bytes
    signed_pre_key_signature: bytes
    pre_keys: FrozenSet[bytes]
    
    def to_dict(self) -> dict:
        """将Bundle转换为可JSON序列化的字典"""
        return {
            'identity_key': b64encode(self.identity_key).decode('utf-8'),
            'signed_pre_key': b64encode(self.signed_pre_key).decode('utf-8'),
            'signed_pre_key_signature': b64encode(self.signed_pre_key_signature).decode('utf-8'),
            'pre_keys': [b64encode(key).decode('utf-8') for key in self.pre_keys]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Bundle':
        """从字典创建Bundle实例"""
        return cls(
            identity_key=b64decode(data['identity_key']),
            signed_pre_key=b64decode(data['signed_pre_key']),
            signed_pre_key_signature=b64decode(data['signed_pre_key_signature']),
            pre_keys=frozenset(b64decode(key) for key in data['pre_keys'])
        )
    
class Header(NamedTuple):
    """
    这个Header类用于存储消息头部信息。
    """
    identity_key: bytes
    ephemeral_key: bytes
    signed_pre_key: bytes
    pre_key: Optional[bytes]

class EncryptedMessage(NamedTuple):
    header: Header
    ciphertext: bytes    
    
@enum.unique
class MessageType(enum.Enum):
    """
    这个MessageType枚举类用于表示消息类型。
    """
    INITIATE = 0
    RESPONSE = 1
    MESSAGE = 2