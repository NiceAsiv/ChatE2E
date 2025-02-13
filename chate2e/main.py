import os
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from typing import Tuple

# ------------------------------------------------------------------
# 辅助函数：HKDF、PKCS7 填充/去填充、AES 加解密
# ------------------------------------------------------------------
def hkdf(input_key: bytes, length: int, info: bytes = b'') -> bytes:
    """
    利用 HKDF 算法从输入 key 派生出固定长度的输出。
    """
    hkdf_inst = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=None,  # 此处使用空 salt，可根据需要修改
        info=info,
        backend=default_backend()
    )
    return hkdf_inst.derive(input_key)

def pad(msg: bytes) -> bytes:
    """PKCS7 填充，使明文长度为 16 字节倍数"""
    num = 16 - (len(msg) % 16)
    return msg + bytes([num] * num)

def unpad(msg: bytes) -> bytes:
    """移除 PKCS7 填充"""
    num = msg[-1]
    if num > 16 or num > len(msg):
        return None  # Invalid padding
    padding = msg[-num:]
    if all(p == num for p in padding):
        return msg[:-num]
    else:
        return None  # Invalid padding

def encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    """使用 AES-CBC 模式加密明文（内部完成 PKCS7 填充）"""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(plaintext))

def decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """使用 AES-CBC 模式解密密文，并移除填充"""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    unpadded_msg = unpad(cipher.decrypt(ciphertext))
    return unpadded_msg if unpadded_msg else None

# ------------------------------------------------------------------
# 对称棘轮（Symmetric Ratchet）实现
# ------------------------------------------------------------------
class SymmRatchet:
    def __init__(self, key: bytes):
        self.state = key

    def next(self, inp: bytes = b'') -> Tuple[bytes, bytes]:
        """
        每次调用将利用当前状态与输入数据（可为空）生成 80 字节输出，
        然后将输出拆分为：
          - 新状态（前 32 字节）
          - 消息密钥（32 字节）
          - IV（16 字节）
        """
        output = hkdf(self.state + inp, 80)
        self.state = output[:32]
        outkey, iv = output[32:64], output[64:]
        return outkey, iv

# ------------------------------------------------------------------
# 双棘轮（Double Ratchet）及 X3DH 初始化
# ------------------------------------------------------------------

def b64(msg):
    return base64.encodebytes(msg).decode('utf-8').strip()

class Bob:
    def __init__(self):
        # 生成 Bob 的密钥对
        self.IKb = X25519PrivateKey.generate()
        self.SPKb = X25519PrivateKey.generate()
        self.OPKb = X25519PrivateKey.generate()

    def x3dh(self, alice):
        # 执行四轮 Diffie-Hellman 密钥交换（X3DH）
        dh1 = self.SPKb.exchange(alice.IKa.public_key())
        dh2 = self.IKb.exchange(alice.EKa.public_key())
        dh3 = self.SPKb.exchange(alice.EKa.public_key())
        dh4 = self.OPKb.exchange(alice.EKa.public_key())
        # 共享密钥通过 KDF(DH1 || DH2 || DH3 || DH4) 派生
        self.sk = hkdf(dh1 + dh2 + dh3 + dh4, 32, b'x3dh')
        print('[Bob]\t共享密钥:', b64(self.sk))
        # 使用共享密钥初始化双棘轮
        self.root_ratchet = SymmRatchet(self.sk)
        root_key, _ = self.root_ratchet.next()
        self.recv_ratchet = SymmRatchet(root_key)
        root_key, _ = self.root_ratchet.next()
        self.send_ratchet = SymmRatchet(root_key)

    def dh_ratchet(self, alice_public):
        """
        使用收到的 Alice DH 公钥进行 DH 交换并更新接收/发送棘轮。
        """
        # 生成新的 DH 密钥对
        self.SPKb = X25519PrivateKey.generate()

        dh_recv = self.SPKb.exchange(alice_public)
        shared_recv = hkdf(dh_recv, 32, b'dh_recv')
        self.recv_ratchet = SymmRatchet(shared_recv)
        print('[Bob]\t接收棘轮种子:', b64(shared_recv))
        
        # 更新发送棘轮
        dh_send = self.SPKb.exchange(alice_public)
        shared_send = hkdf(dh_send, 32, b'dh_send')
        self.send_ratchet = SymmRatchet(shared_send)
        print('[Bob]\t发送棘轮种子:', b64(shared_send))

    def send(self, alice, msg: bytes):
        """Bob 发送消息时，通过发送棘轮生成消息密钥加密消息"""
        key, iv = self.send_ratchet.next()
        cipher = encrypt(key, iv, msg)
        print('[Bob]\t发送密文给 Alice:', b64(cipher))
        # 发送密文及当前 DH 公钥
        alice.recv(cipher, {'dh': self.SPKb.public_key()})
        
    def recv(self, cipher: bytes, alice_public_key):
        """Bob 收到消息时，使用 Alice 公钥进行 DH 交换并解密消息"""
        alice_public_key = alice_public_key.get('dh')
        self.dh_ratchet(alice_public_key)
        key, iv = self.recv_ratchet.next()
        msg = decrypt(key, iv, cipher)
        if msg:
            print('[Bob]\t解密消息:', msg)
        else:
            print('[Bob]\t解密消息失败：消息为空')

class Alice:
    def __init__(self):
        self.IKa = X25519PrivateKey.generate()
        self.EKa = X25519PrivateKey.generate()
        self.prev_bob_pub = None  # 记录上次接收到的 Bob 临时公钥

    def x3dh(self, bob):
        dh1 = self.IKa.exchange(bob.SPKb.public_key())
        dh2 = self.EKa.exchange(bob.IKb.public_key())
        dh3 = self.EKa.exchange(bob.SPKb.public_key())
        dh4 = self.EKa.exchange(bob.OPKb.public_key())
        self.sk = hkdf(dh1 + dh2 + dh3 + dh4, 32, b'x3dh')
        print('[Alice]\t共享密钥:', b64(self.sk))
        self.root_ratchet = SymmRatchet(self.sk)
        root_key, _ = self.root_ratchet.next()
        self.send_ratchet = SymmRatchet(root_key)
        root_key, _ = self.root_ratchet.next()
        self.recv_ratchet = SymmRatchet(root_key)

    def dh_ratchet(self, bob_public):
        # 只有当收到的临时公钥变化时才更新棘轮
        if self.prev_bob_pub is None or self.prev_bob_pub != bob_public:
            self.prev_bob_pub = bob_public
            # 使用 bob_public 更新接收链
            dh_recv = self.EKa.exchange(bob_public)
            shared_recv = hkdf(dh_recv, 32, b'dh_recv')
            self.recv_ratchet = SymmRatchet(shared_recv)
            print('[Alice]\t接收棘轮种子:', b64(shared_recv))
            
            # 更新发送链（可选：根据协议决定是否同时更新发送链）
            self.EKa = X25519PrivateKey.generate()
            dh_send = self.EKa.exchange(bob_public)
            shared_send = hkdf(dh_send, 32, b'dh_send')
            self.send_ratchet = SymmRatchet(shared_send)
            print('[Alice]\t发送棘轮种子:', b64(shared_send))
        else:
            print('[Alice]\t棘轮公钥未变化，跳过更新')

    def send(self, bob, msg: bytes):
        print('[Alice]\t发送明文:', msg)  # Check if message is empty
        key, iv = self.send_ratchet.next()
        cipher = encrypt(key, iv, msg)
        print('[Alice]\t发送密文给 Bob:', b64(cipher))
        # 将自己的临时 DH 公钥附加到消息 header 中发送给 Bob
        header = {'dh': self.EKa.public_key()}
        bob.recv(cipher, header)

    def recv(self, cipher: bytes, header: dict):
        bob_pub = header.get('dh')
        self.dh_ratchet(bob_pub)
        key, iv = self.recv_ratchet.next()
        msg = decrypt(key, iv, cipher)
        if msg:
            print('[Alice]\t解密消息:', msg)
        else:
            print('[Alice]\t解密消息失败：消息为空')

# ------------------------------------------------------------------
# 测试：Alice 和 Bob 使用 X3DH 和双棘轮进行消息交换
# ------------------------------------------------------------------
def main():
    alice = Alice()
    bob = Bob()

    # Alice 执行 X3DH
    alice.x3dh(bob)

    # Bob 执行 X3DH
    bob.x3dh(alice)

    # Alice 使用 Bob 的公钥进行 DH 棘轮更新
    bob.dh_ratchet(alice.EKa.public_key())
    alice.dh_ratchet(bob.SPKb.public_key())

    # Alice 发送消息给 Bob
    alice.send(bob, b'Hello Bob!')

    # Bob 收到消息并发送回复
    bob.send(alice, b'Hello to you too, Alice!')

if __name__ == '__main__':
    main()
