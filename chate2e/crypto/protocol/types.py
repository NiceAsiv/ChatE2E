from __future__ import annotations

from typing import FrozenSet, NamedTuple
from base64 import b64encode, b64decode

class Bundle(NamedTuple):
    """
    这个Bundle类用于存储X3DH协议中的密钥信息和signature。
    """
    identity_key_pub: bytes
    signed_pre_key_pub: bytes
    signed_pre_key_signature: bytes
    one_time_pre_keys_pub: FrozenSet[bytes]
    
    def to_dict(self) -> dict:
        """将Bundle转换为可JSON序列化的字典"""
        return {
            'identity_key_pub': self.identity_key_pub,
            'signed_pre_key_pub': self.signed_pre_key_pub,
            'signed_pre_key_signature': self.signed_pre_key_signature,
            'one_time_pre_keys_pub': [key for key in self.one_time_pre_keys_pub]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Bundle':
        """从字典中构造Bundle对象"""
        return cls(
            identity_key_pub=data['identity_key_pub'],
            signed_pre_key_pub=data['signed_pre_key_pub'],
            signed_pre_key_signature=data['signed_pre_key_signature'],
            one_time_pre_keys_pub=frozenset(data['one_time_pre_keys_pub'])
        )