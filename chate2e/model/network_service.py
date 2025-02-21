import aiohttp
from typing import Optional, Dict
from chate2e.crypto.protocol.types import Bundle
from chate2e.model.message import Message
import asyncio

class ClientNetworkService:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        self.session = aiohttp.ClientSession(loop=self.loop)


    async def close(self):
        await self.session.close()

    async def register_user(self, username: str, key_bundle: dict) -> Optional[str]:
        """注册新用户"""
        try:
            async with self.session.post(
                f"{self.base_url}/register",
                json={
                    "username": username,
                    "key_bundle": key_bundle
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("uuid")
                return None
        except Exception as e:
            print(f"注册失败: {e}")
            return None

    async def get_key_bundle(self, user_uuid: str) -> Bundle:
        """获取用户的密钥bundle"""
        try:
            async with self.session.get(
                f"{self.base_url}/key_bundle/{user_uuid}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("key_bundle")
                return None
        except Exception as e:
            print(f"获取密钥bundle失败: {e}")
            return None

    async def update_key_bundle(self, user_uuid: str, key_bundle: dict) -> bool:
        """更新密钥bundle"""
        try:
            async with self.session.put(
                f"{self.base_url}/key_bundle",
                json={
                    "uuid": user_uuid,
                    "key_bundle": key_bundle
                }
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"更新密钥bundle失败: {e}")
            return False

    async def send_message(self, message_data: Message) -> bool:
        """发送加密消息"""
        try:
            async with self.session.post(
                f"{self.base_url}/message",
                json=message_data
            ) as response:
                return response.status == 200
        except Exception as e:
            print(f"发送消息失败: {e}")
            return False