# double_ratchet.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

class DoubleRatchet:
    def __init__(self, shared_key):
        self.DHs = X25519PrivateKey.generate()
        self.DHr = None
        self.RK = shared_key
        self.CKs = None
        self.CKr = None
        self.Ns = 0
        self.Nr = 0
        self.PN = 0
        
    def ratchet_encrypt(self, plaintext):
        if self.CKs is None:
            self.CKs = self._kdf_ck(self.RK)
        
        message_key = self._kdf_mk(self.CKs)
        header = {
            'dh': self.DHs.public_key(),
            'n': self.Ns,
            'pn': self.PN
        }
        
        # AEAD加密
        aesgcm = AESGCM(message_key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        
        self.Ns += 1
        return header, ciphertext

    def ratchet_decrypt(self, header, ciphertext):
        if header.dh != self.DHr:
            self._dh_ratchet(header)
            
        message_key = self._kdf_mk(self.CKr)
        
        # AEAD解密
        aesgcm = AESGCM(message_key)
        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            return None
            
        self.Nr += 1
        return plaintext