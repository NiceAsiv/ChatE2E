from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from chate2e.crypto.crypto_helper import CryptoHelper
class X3DHProtocol:
    def __init__(self):
        # 生成身份密钥对(IPK)
        self.ipk = X25519PrivateKey.generate()
        # 生成签名预密钥对(SPK) 
        self.spk = X25519PrivateKey.generate()
        # 生成一次性预密钥对(OPK)
        self.opk = [X25519PrivateKey.generate() for _ in range(100)]
        # 生成加密辅助类
        self.crypto_helper = CryptoHelper()
        
    def compute_shared_secret(self, identity_key: x25519.X25519PrivateKey, signed_prekey: x25519.X25519PrivateKey,
                              ephemeral_key: x25519.X25519PrivateKey, one_time_prekey: x25519.X25519PrivateKey,
                              identity_key_b: x25519.X25519PublicKey, signed_prekey_b: x25519.X25519PublicKey,
                              ephemeral_key_b: x25519.X25519PublicKey, one_time_prekey_b: x25519.X25519PublicKey) -> bytes:
        """
        计算共享密钥。
        :param identity_key: 本地身份私钥
        :param signed_prekey: 本地已签名的预共享密钥私钥
        :param ephemeral_key: 本地临时密钥私钥
        :param one_time_prekey: 本地一次性预共享密钥私钥
        :param identity_key_b: 对方身份公钥
        :param signed_prekey_b: 对方已签名的预共享密钥公钥
        :param ephemeral_key_b: 对方临时密钥公钥
        :param one_time_prekey_b: 对方一次性预共享密钥公钥
        :return: 共享密钥
        """
        # DH1 = DH(IK,SPK)
        dh1 = self.crypto_helper.ecdh(identity_key, signed_prekey_b)
        # DH2 = DH(EK,IK)
        dh2 = self.crypto_helper.ecdh(ephemeral_key, identity_key_b)
        # DH3 = DH(EK,SPK)
        dh3 = self.crypto_helper.ecdh(ephemeral_key, signed_prekey_b)
        # DH4 = DH(EK,OPK)
        dh4 = self.crypto_helper.ecdh(identity_key, one_time_prekey_b) if one_time_prekey_b else b""
        
        # SK = KDF(DH1 || DH2 || DH3 || DH4)
        combined = dh1 + dh2 + dh3 + dh4
        shared_secret = self.crypto_helper.hkdf(combined, 32)
        return shared_secret