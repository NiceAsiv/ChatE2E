# server.py
class SignalServer:
    def __init__(self):
        self.clients = {}  # 用户ID -> 连接
        self.key_bundles = {}  # 用户ID -> 预共享密钥包
        
    def handle_client(self, client_socket):
        # 1. 用户注册/登录
        user_id = self.authenticate_user(client_socket)
        
        # 2. 分发预共享密钥包
        self.distribute_key_bundles(user_id)
        
        # 3. 转发加密消息
        while True:
            message = client_socket.recv(4096)
            recipient_id = message.recipient_id
            if recipient_id in self.clients:
                self.clients[recipient_id].send(message)