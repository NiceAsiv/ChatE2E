# x3dh.py
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

class X3DHProtocol:
    def __init__(self):
        # 生成身份密钥对(IK)
        self.ik = X25519PrivateKey.generate()
        # 生成签名预密钥对(SPK) 
        self.spk = X25519PrivateKey.generate()
        # 生成一次性预密钥对(OPK)
        self.opk = [X25519PrivateKey.generate() for _ in range(100)]

    def generate_initial_message(self, server_bundle):
        # 生成临时密钥对(EK)
        self.ek = X25519PrivateKey.generate()
        
        # DH1 = DH(IK,SPK)
        dh1 = self.ik.exchange(server_bundle.spk)
        # DH2 = DH(EK,IK)
        dh2 = self.ek.exchange(server_bundle.ik)
        # DH3 = DH(EK,SPK)
        dh3 = self.ek.exchange(server_bundle.spk)
        # DH4 = DH(EK,OPK)
        dh4 = self.ek.exchange(server_bundle.opk)
        
        # SK = KDF(DH1 || DH2 || DH3 || DH4)
        sk = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b'X3DH'
        ).derive(dh1 + dh2 + dh3 + dh4)
        
        return sk