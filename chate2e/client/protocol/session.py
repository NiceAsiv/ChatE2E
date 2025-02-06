# session.py
class Session:
    def __init__(self):
        self.x3dh = X3DHProtocol()
        self.ratchet = None
        
    def initialize(self, bundle):
        # X3DH密钥协商
        shared_secret = self.x3dh.generate_initial_message(bundle)
        # 初始化双棘轮
        self.ratchet = DoubleRatchet(shared_secret)
        
    def send_message(self, plaintext):
        return self.ratchet.ratchet_encrypt(plaintext)
        
    def receive_message(self, header, ciphertext):
        return self.ratchet.ratchet_decrypt(header, ciphertext)