from typing import Dict, Optional
import json
import uuid
import time
import enum


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
    def __init__(self,algorithm: str, iv: str, tag: str, is_initiator: bool):
        self.algorithm = algorithm
        self.iv = iv
        self.tag = tag
        self.is_initiator = is_initiator

    def to_dict(self) -> dict:
        return {
            'algorithm': self.algorithm,
            'iv': self.iv,
            'tag': self.tag,
            'is_initiator': self.is_initiator
        }
        
class X3DHparams:
    def __init__(self, identity_key_pub: str,ephemeral_key_pub: str):
        self.identity_key_pub = identity_key_pub
        self.ephemeral_key_pub = ephemeral_key_pub

    def to_dict(self) -> dict:
        return {
            'identity_key_pub': self.identity_key_pub,
            'ephemeral_key_pub': self.ephemeral_key_pub
            }
        
class Message:
    def __init__(self, message_id: str, sender_id: str, session_id : str,
                 receiver_id: str, encrypted_content: str, 
                 message_type: MessageType.MESSAGE,encryption: Encryption = None, timestamp: float = time.time(),X3DHparams: X3DHparams = None):
        self.header = Header(sender_id, receiver_id, session_id, message_id, message_type, timestamp)
        self.encrypted_content = encrypted_content
        self.encryption = encryption
        self.X3DHparams = X3DHparams

    def to_dict(self) -> dict:
        return {
            'header': self.header.to_dict(),
            'encrypted_content': self.encrypted_content,
            'encryption': self.encryption.to_dict() if self.encryption else None,
            'X3DHparams': self.X3DHparams.to_dict() if self.X3DHparams else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        # 从嵌套的header数据创建Header对象
        header_data = data['header']
        header_data['message_type'] = MessageType(header_data['message_type'])  # 将整数转换为枚举
        
        # 处理可选的加密参数
        encryption_data = data.get('encryption')
        encryption = Encryption(**encryption_data) if encryption_data else None
        
        # 处理可选的X3DH参数
        x3dh_data = data.get('X3DHparams')
        x3dh = X3DHparams(**x3dh_data) if x3dh_data else None
        
        # 使用header中的数据创建Message对象
        return cls(
            message_id=header_data['message_id'],
            sender_id=header_data['sender_id'],
            session_id=header_data['session_id'],
            receiver_id=header_data['receiver_id'],
            encrypted_content=data['encrypted_content'],
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