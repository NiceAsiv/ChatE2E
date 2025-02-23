from base64 import b64encode, b64decode

class KeyPair:
    """密钥对存储类"""
    def __init__(self, private_key: bytes, public_key: bytes):
        self.private_key = private_key
        self.public_key = public_key

    def to_dict(self) -> dict:
        return {
            'private_key': b64encode(self.private_key).decode('utf-8'),
            'public_key': b64encode(self.public_key).decode('utf-8')
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'KeyPair':
        return cls(
            private_key=b64decode(data['private_key']),
            public_key=b64decode(data['public_key'])
        )