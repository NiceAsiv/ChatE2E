from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from chate2e.crypto.crypto_helper import CryptoHelper
from chate2e.crypto.mac_helper import MACHelper
from chate2e.crypto.protocol.types import Bundle


class X3DHProtocol:
    def __init__(self, name , MAX_ONE_TIME_PREKEYS=100):
        self.name = name
        self.backend = default_backend()
        self.crypto_helper = CryptoHelper()
        # 生成身份密钥对(identity key pair, IPK)
        self.ipk_priv, self.ipk_pub = self.crypto_helper.create_x25519_keypair()
        # 生成签名预密钥对(signed prekey pair, SPK)
        self.spk_priv, self.spk_pub = self.crypto_helper.create_x25519_keypair()
        #SPK签名
        self.spk_signature = MACHelper.sign(self.spk_pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ), self.ipk_priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        ))
        self.OPKs_priv = []
        self.OPKs_pub = []
        for _ in range(MAX_ONE_TIME_PREKEYS):
            sk , pk = self.crypto_helper.create_x25519_keypair()
            self.OPKs_priv.append((sk,pk))
            self.OPKs_pub.append(pk)
            self.key_bundles = {}
        # self.OPKs_priv = [self.crypto_helper.create_x25519_keypair() for _ in range(MAX_ONE_TIME_PREKEYS)]
        # self.OPKs_pub = [key[1] for key in self.OPK_priv]
        
    @property
    def bundle(self) -> Bundle:
        """
        生成密钥 bundle 信息，用于传递给对方。
        :return: 密钥 bundle
        """
        return {
            'identity_key_pub': self.ipk_pub,
            'signed_pre_key_pub': self.spk_pub,
            'signed_pre_key_signature': self.spk_signature,
            'one_time_pre_keys_pub': self.OPKs_pub
        }  
          
    async def get_key_bundle(self, server , user_name):
        """
        从服务器获取对方密钥 bundle 信息。
        """
        if user_name in self.key_bundles and user_name in self.dr_keys:
            print("Already stored "+ user_name + " bundle locally, no need to handshake again")
            return True
        self.key_bundles[user_name] = await server.get_key_bundle(user_name)
        return True
    
    async def initial_handshake(self, server, user_name):
        """
        初始握手，向服务器请求对方密钥 bundle 信息,并生成临时密钥
        """
        if await self.get_key_bundle(server, user_name):
            sk = x25519.X25519PrivateKey.generate()
            # 从服务器获取的密钥bundle
            bundle = await server.get_key_bundle(user_name)
            self.key_bundles[user_name] = {}
            self.key_bundles[user_name]['identity_key_pub'] = bundle['identity_key_pub']
            self.key_bundles[user_name]['signed_pre_key_pub'] = bundle['signed_pre_key_pub']
            self.key_bundles[user_name]['signed_pre_key_signature'] = bundle['signed_pre_key_signature']
            self.key_bundles[user_name]['one_time_pre_keys_pub'] = bundle['one_time_pre_keys_pub']
            self.key_bundles[user_name]['ephemeral_pri_key'] = sk
            self.key_bundles[user_name]['ephemeral_pub_key'] = sk.public_key()
        return True 
    
    def compute_shared_secret(self, 
                              identity_pri_key: x25519.X25519PrivateKey, 
                              signed_pri_prekey: x25519.X25519PrivateKey,
                              ephemeral_pri_key: x25519.X25519PrivateKey, 
                              one_time_pri_prekey: x25519.X25519PrivateKey,
                              identity_key_b: x25519.X25519PublicKey, 
                              signed_prekey_b: x25519.X25519PublicKey,
                              ephemeral_key_b: x25519.X25519PublicKey, 
                              one_time_prekey_b: x25519.X25519PublicKey = None) -> bytes:
        """
        根据 Signal 协议计算共享密钥：
        DH1 = DH(身份私钥, 对方签名预密钥公钥)
        DH2 = DH(本地临时密钥, 对方身份公钥) 或 DH(对方身份公钥, 对方传来的临时公钥)
        DH3 = DH(本地临时密钥, 对方签名预密钥公钥) 或 DH(对方签名预密钥, 对方传来的临时公钥)
        DH4 = DH(身份私钥, 对方一次性预密钥公钥) （可选）
        SK  = HKDF(DH1 || DH2 || DH3 || DH4)
        :param identity_key: 本地身份密钥
        :param signed_prekey: 本地签名预密钥
        :param ephemeral_key: 本地临时密钥
        :param one_time_prekey: 本地一次性预密钥
        :param identity_key_b: 对方身份密钥
        :param signed_prekey_b: 对方签名预密钥
        :param ephemeral_key_b: 对方临时密钥
        :param one_time_prekey_b: 对方一次性预密钥
        :return: 共享密钥
        """
        dh1 = self.crypto_helper.ecdh(identity_pri_key, signed_prekey_b)
        dh2 = self.crypto_helper.ecdh(ephemeral_pri_key, identity_key_b) if ephemeral_key_b is not None else b""
        dh3 = self.crypto_helper.ecdh(ephemeral_pri_key, signed_prekey_b) if ephemeral_key_b is not None else b""
        dh4 = self.crypto_helper.ecdh(identity_pri_key, one_time_prekey_b) if one_time_prekey_b is not None else b""
        combined = dh1 + dh2 + dh3 + dh4
        shared_secret = self.crypto_helper.hkdf(combined, 32)
        return shared_secret
    
    def get_shared_secret_active(self, user_name ) -> bytes:
        """
        主动方计算共享密钥：
        1. 生成临时密钥 (EK)
        2. 使用本地 IK、SPK 与对方 bundle 中的 IK、SPK、OPK 计算共享密钥：
            DH1 = DH(本地 IK, 对方 SPK)
            DH2 = DH(本地 EK, 对方 IK)
            DH3 = DH(本地 EK, 对方 SPK)
            DH4 = DH(本地 EK, 对方 OPK) （如果存在）
        :param user_name: 对方用户名
        :return: (共享密钥, 本地生成的临时密钥)
        """
        if user_name not in self.key_bundles:
            print("No bundle information for " + user_name)
            return None
        key_bundle = self.key_bundles[user_name]
        dh1 = self.crypto_helper.ecdh(self.ipk_priv, key_bundle['signed_pre_key_pub'])
        dh2 = self.crypto_helper.ecdh(key_bundle['ephemeral_pri_key'], self.ipk_pub)
        dh3 = self.crypto_helper.ecdh(key_bundle['ephemeral_pri_key'], key_bundle['signed_pre_key_pub'])
        dh4 = self.crypto_helper.ecdh(key_bundle['ephemeral_pri_key'], key_bundle['one_time_pre_keys_pub'][0]) if key_bundle['one_time_pre_keys_pub'] else b""
        
        # if not MACHelper.verify (self.ipk_priv, key_bundle['signed_pre_key_signature']):
        #     print("Invalid signature")
        #     return None
        
        combined = dh1 + dh2 + dh3 + dh4
        km = b'\xff' * 32 + combined
        hkdf = HKDF(algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'\0' * 32,
                    info=b'',
                    backend=self.backend)
        shared_secret = hkdf.derive(km)
        return shared_secret