from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from chate2e.crypto.crypto_helper import CryptoHelper
from chate2e.crypto.mac_helper import MACHelper
from chate2e.crypto.protocol.types import Bundle
from typing import Dict, Optional, Tuple
from chate2e.utils.network_service import ClientNetworkService

class X3DHProtocol:
    def __init__(self, name , MAX_ONE_TIME_PREKEYS=10):
        self.name = name
        self.user_uuid = None
        self.backend = default_backend()
        self.crypto_helper = CryptoHelper()
        # 生成身份密钥对(identity key pair, IPK)
        self.ipk_priv, self.ipk_pub = self.crypto_helper.create_x25519_keypair()
        # 生成签名预密钥对(signed prekey pair, SPK)
        self.spk_priv, self.spk_pub = self.crypto_helper.create_x25519_keypair()
        #SPK签名
        self.spk_signature = self._generate_prekey_signature()
        
        # 生成一次性预密钥对(one-time prekey pairs, OPKs)
        self.OPKs_priv = []
        self.OPKs_pub = []
        self.OPKs_priv = [self.crypto_helper.create_x25519_keypair() for _ in range(MAX_ONE_TIME_PREKEYS)]
        self.OPKs_pub = [key[1] for key in self.OPKs_priv]
        
        #ephemeral key pair
        self.ephemeral_key_pair:Dict[str, Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]] = {}
            
        # 用于存储对方密钥 bundle 信息    user_uuid: bundle
        self.peer_key_bundles: Dict[str, Bundle] = {}
        
        #存储会话密钥 peer_uuid: session_key
        self.session_keys: Dict[str, bytes] = {}
        
    def _generate_prekey_signature(self) -> bytes:
        """生成预签名密钥的签名"""
        prekey_bytes = self.spk_pub.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        identity_key_bytes = self.ipk_priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        return MACHelper.sign(prekey_bytes, identity_key_bytes)
    
    def get_bundle(self) -> dict:
        """获取用于注册的密钥束"""
        bundle = {
            'identity_key_pub': self.ipk_pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ),
            'signed_pre_key_pub': self.spk_pub.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ),
            'signed_pre_key_signature': self.spk_signature,
            'one_time_pre_keys_pub': frozenset(
                key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
                for key in self.OPKs_pub
            )
        }
        return bundle
    
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
        
    async def upload_key_bundle(self, network_service: ClientNetworkService) -> bool:
        """上传密钥束到服务器"""
        try:
            print(f"上传密钥束到服务器")
            self.user_uuid = await network_service.register_user(self.name, self.get_bundle())
            return True
        except Exception as e:
            print(f"上传密钥束失败: {str(e)}")
            return False
        
    async def x3dh_hello_exchange(self, peer_id: str, network_service) -> bool:
        """处理初始密钥交换"""
        print(f"开始与{peer_id}进行密钥交换")
        try:
            if peer_id in self.peer_bundles:
                print(f"已经与{peer_id}完成密钥交换，无需再次交换")
                return True
            
            # 获取对方的密钥束
            bundle_data = await network_service.get_key_bundle(peer_id)
            if not bundle_data:
                return False
                
            # 转换为Bundle对象
            peer_bundle = Bundle.from_dict(bundle_data)
            self.peer_bundles[peer_id] = peer_bundle
            
            # 生成临时密钥对
            ephemeral_key = self.crypto_helper.create_x25519_keypair()
            self.ephemeral_key_pair[peer_id] = ephemeral_key
            
            # 计算共享密钥
            shared_secret = self._calculate_shared_secret(
                peer_bundle,
                ephemeral_key
            )
            
            # 存储会话密钥
            self.session_keys[peer_id] = shared_secret
            
            return True
            
        except Exception as e:
            print(f"初始密钥交换失败: {str(e)}")
            return False          
    
    def _calculate_shared_secret(
        self, 
        peer_bundle: Bundle,
        ephemeral_key: Tuple[x25519.X25519PrivateKey, x25519.X25519PublicKey]
    ) -> bytes:
        """计算共享密钥"""
        dh1 = self.crypto_helper.ecdh(self.ipk_priv,peer_bundle.signed_pre_key_pub)
        dh2 = self.crypto_helper.ecdh(ephemeral_key[0],peer_bundle.identity_key_pub)
        dh3 = self.crypto_helper.ecdh(ephemeral_key[0],peer_bundle.signed_pre_key_pub)
        
        # 使用第一个一次性预密钥
        if peer_bundle.pre_keys:
            one_time_prekey = next(iter(peer_bundle.pre_keys))
            dh4 = self.crypto_helper.ecdh(
                self.ipk_priv,
                one_time_prekey
            )
        else:
            dh4 = b""

        # 组合DH输出
        dh_out = dh1 + dh2 + dh3 + dh4
        
        # 派生共享密钥
        return self.crypto_helper.hkdf(dh_out, 32)
    
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