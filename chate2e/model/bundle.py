from typing import FrozenSet, NamedTuple
from base64 import b64encode, b64decode

from chate2e.model.key_pair import KeyPair


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
            'identity_key_pub': b64encode(self.identity_key_pub).decode('utf-8'),
            'signed_pre_key_pub': b64encode(self.signed_pre_key_pub).decode('utf-8'),
            'signed_pre_key_signature': b64encode(self.signed_pre_key_signature).decode('utf-8'),
            'one_time_pre_keys_pub': [b64encode(key).decode('utf-8') 
                                    for key in self.one_time_pre_keys_pub]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Bundle':
        """从字典中构造Bundle对象"""
        return cls(
            identity_key_pub=b64decode(data['identity_key_pub']),
            signed_pre_key_pub=b64decode(data['signed_pre_key_pub']),
            signed_pre_key_signature=b64decode(data['signed_pre_key_signature']),
            one_time_pre_keys_pub=frozenset(b64decode(key) 
                                          for key in data['one_time_pre_keys_pub'])
        )

class LocalBundle(NamedTuple):
    """本地Bundle"""
    identity_key_pair: KeyPair
    signed_pre_key_pair: KeyPair
    signed_pre_key_signature: bytes
    one_time_pre_key_pairs: FrozenSet[KeyPair]

    def to_dict(self) -> dict:
        """将LocalBundle转换为可JSON序列化的字典"""
        return {
            'identity_key_pair': self.identity_key_pair.to_dict(),
            'signed_pre_key_pair': self.signed_pre_key_pair.to_dict(),
            'signed_pre_key_signature': b64encode(self.signed_pre_key_signature).decode('utf-8'),
            'one_time_pre_key_pairs': [key_pair.to_dict()
                                    for key_pair in self.one_time_pre_key_pairs]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LocalBundle':
        """从字典中构造LocalBundle对象"""
        return cls(
            identity_key_pair=KeyPair.from_dict(data['identity_key_pair']),
            signed_pre_key_pair=KeyPair.from_dict(data['signed_pre_key_pair']),
            signed_pre_key_signature=b64decode(data['signed_pre_key_signature']),
            one_time_pre_key_pairs=frozenset(KeyPair.from_dict(key_pair)
                                          for key_pair in data['one_time_pre_key_pairs'])
        )