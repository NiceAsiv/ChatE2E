from typing import Dict, Optional
import json
import uuid
import time
import enum
from base64 import b64encode, b64decode


@enum.unique
class MessageType(enum.Enum):
    """
    这个MessageType枚举类用于表示消息类型。
    """
    INITIATE = 0
    ACK_INITIATE = 1
    MESSAGE = 2
    BROADCAST = 3                
                
class Header:
    def __init__(self, sender_id: str, receiver_id: str, session_id: str,
                message_id: str, message_type: MessageType, timestamp: float):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.session_id = session_id
        self.message_id = message_id
        self.message_type = message_type
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'session_id': self.session_id,
            'message_id': self.message_id,
            'message_type': self.message_type.value,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Header':
        return cls(**data)

    def serialize(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, json_str: str) -> 'Header':
        data = json.loads(json_str)
        return cls.from_dict(data)

    @staticmethod
    def generate_id() -> str:
        """生成消息ID"""
        return str(uuid.uuid4())
    
class Encryption:
    def __init__(self, algorithm: str, iv: bytes, tag: bytes, is_initiator: bool):
        self.algorithm = algorithm
        self.iv = iv
        self.tag = tag
        self.is_initiator = is_initiator

    def to_dict(self) -> dict:
        # 处理可能已经是字符串的情况
        def encode_if_bytes(value):
            if isinstance(value, bytes):
                return b64encode(value).decode('utf-8')
            return value  # 已经是字符串
        
        result = {
            'algorithm': self.algorithm,
            'iv': encode_if_bytes(self.iv),
            'tag': encode_if_bytes(self.tag),
            'is_initiator': self.is_initiator
        }
        
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'Encryption':
        return cls(
            algorithm=data['algorithm'],
            iv=b64decode(data['iv']),
            tag=b64decode(data['tag']),
            is_initiator=data['is_initiator']
        )
        
class X3DHparams:
    def __init__(self, identity_key_pub: bytes, signed_pre_key_pub: bytes, one_time_pre_keys_pub: bytes, ephemeral_key_pub: bytes):
        self.identity_key_pub = identity_key_pub
        self.signed_pre_key_pub = signed_pre_key_pub
        self.ephemeral_key_pub = ephemeral_key_pub
        self.one_time_pre_keys_pub = one_time_pre_keys_pub

    def to_dict(self) -> dict:
        # 处理可能已经是字符串的情况
        def encode_if_bytes(value):
            if isinstance(value, bytes):
                return b64encode(value).decode('utf-8')
            return value  # 已经是字符串
        
        return {
            'identity_key_pub': encode_if_bytes(self.identity_key_pub),
            'signed_pre_key_pub': encode_if_bytes(self.signed_pre_key_pub),
            'one_time_pre_keys_pub': encode_if_bytes(self.one_time_pre_keys_pub),
            'ephemeral_key_pub': encode_if_bytes(self.ephemeral_key_pub)
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'X3DHparams':
        return cls(
            identity_key_pub=b64decode(data['identity_key_pub']),
            signed_pre_key_pub=b64decode(data['signed_pre_key_pub']),
            one_time_pre_keys_pub=b64decode(data['one_time_pre_keys_pub']),
            ephemeral_key_pub=b64decode(data['ephemeral_key_pub'])
        )

class Message:
    def __init__(self, message_id: str, sender_id: str, session_id : str,
                 receiver_id: str, encrypted_content: bytes,
                 message_type: MessageType.MESSAGE,encryption: Encryption = None, timestamp: float = time.time(),X3DHparams: X3DHparams = None):
        self.header = Header(sender_id, receiver_id, session_id, message_id, message_type, timestamp)
        self.encrypted_content = encrypted_content
        self.encryption = encryption
        self.X3DHparams = X3DHparams

    def to_dict(self) -> dict:
        return {
            'header': self.header.to_dict(),
            'encrypted_content': self.encrypted_content if isinstance(self.encrypted_content, str)
            else b64encode(self.encrypted_content).decode('utf-8') if isinstance(self.encrypted_content, bytes)
            else str(self.encrypted_content),
            'encryption': self.encryption.to_dict() if self.encryption else None,
            'X3DHparams': self.X3DHparams.to_dict() if self.X3DHparams else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        # 从嵌套的header数据创建Header对象
        header_data = data['header']
        header_data['message_type'] = MessageType(header_data['message_type'])  # 将整数转换为枚举

        # Handle encryption data
        encryption_data = data.get('encryption')
        encryption = Encryption.from_dict(encryption_data) if encryption_data else None
        
        # 处理可选的X3DH参数
        x3dh_data = data.get('X3DHparams')
        x3dh = X3DHparams.from_dict(x3dh_data) if x3dh_data else None

        # Handle encrypted content
        encrypted_content_raw = data['encrypted_content']
        
        if isinstance(encrypted_content_raw, str):
            try:
                encrypted_content = b64decode(encrypted_content_raw)
            except Exception as e:
                print(f"[ERROR] Base64解码失败: {e}")
                raise
        else:
            encrypted_content = encrypted_content_raw

        # 使用header中的数据创建Message对象
        return cls(
            message_id=header_data['message_id'],
            sender_id=header_data['sender_id'],
            session_id=header_data['session_id'],
            receiver_id=header_data['receiver_id'],
            encrypted_content= encrypted_content,
            message_type=header_data['message_type'],
            timestamp=header_data['timestamp'],
            encryption=encryption,
            X3DHparams=x3dh
        )

    def serialize(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, json_str: str) -> 'Message':
        data = json.loads(json_str)
        return cls.from_dict(data)

    @staticmethod
    def generate_id() -> str:
        """生成消息ID"""
        return str(uuid.uuid4())