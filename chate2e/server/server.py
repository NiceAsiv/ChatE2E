import asyncio
import json
import websockets

# server.py
class ChatServer:
    def __init__(self):
        self.clients = {}  # 用户ID -> 连接
        self.key_bundles = {}  # 用户ID -> 预共享密钥包
        
    async def register(self, username: str, websocket: websockets.WebSocketServerProtocol):
        """注册新用户"""
        if username in self.users:
            raise ValueError(f"用户名 {username} 已被使用")
        
        self.users[username] = websocket
        
        # 广播用户列表更新
        await self.broadcast_user_list()
        
        # 广播新用户加入消息
        join_message = ChatMessage(
            type=MessageType.JOIN.value,
            sender="system",
            receiver="all",
            content=f"{username} 加入了聊天"
        )
        await self.broadcast(join_message)
        
    
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