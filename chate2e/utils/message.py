from dataclasses import dataclass, asdict
from typing import Optional, Dict
import json
import time

@dataclass
class Message:
    message_id: str
    session_id: str
    sender_id: str
    receiver_id: str
    content: str
    timestamp: float = time.time()
    encryption: Optional[Dict] = None  # 存储加密相关信息
    
    def to_dict(self):
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
        
    def serialize(self):
        return json.dumps(self.to_dict())
        
    @classmethod
    def deserialize(cls, json_str):
        data = json.loads(json_str)
        return cls.from_dict(data)