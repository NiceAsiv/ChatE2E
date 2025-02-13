import pytest
from chate2e.crypto.protocol.x3dh import X3DHProtocol
from chate2e.server.server import ChatServer
import asyncio

@pytest.fixture
async def setup():
    server = ChatServer()
    alice = X3DHProtocol("Alice")
    bob = X3DHProtocol("Bob")
    return server, alice, bob

@pytest.mark.asyncio
async def test_x3dh_initial_handshake(setup):
    """测试 X3DH 初始握手"""
    server, alice, bob = await setup

    # 1. Alice 和 Bob 向服务器注册
    await server.register(alice.name, None)  # WebSocket 连接在此测试中未使用
    await server.register(bob.name, None)

    # 2. Alice 和 Bob 将密钥 Bundle 分发到服务器
    await server.distribute_key_bundle(alice.name, alice.bundle)
    await server.distribute_key_bundle(bob.name, bob.bundle)

    # 3. Alice 尝试与 Bob 建立会话
    await alice.initial_handshake(server, bob.name)

    # 4. 验证 Alice 是否成功获取 Bob 的密钥 Bundle
    assert bob.name in alice.key_bundles
    assert alice.key_bundles[bob.name]['identity_key_pub'] == bob.ipk_pub
    assert alice.key_bundles[bob.name]['signed_pre_key_pub'] == bob.spk_pub
    assert alice.key_bundles[bob.name]['signed_pre_key_signature'] == bob.spk_signature
    assert alice.key_bundles[bob.name]['one_time_pre_keys_pub'] == bob.OPKs_pub

    # 5. 验证 Alice 是否生成了临时密钥
    assert 'ephemeral_pri_key' in alice.key_bundles[bob.name]
    assert 'ephemeral_pub_key' in alice.key_bundles[bob.name]
    
@pytest.mark.asyncio
async def test_x3dh_shared_secret(setup):
    """测试 X3DH 共享密钥生成"""
    server, alice, bob = await setup

    # 1. Alice 和 Bob 向服务器注册
    await server.register(alice.name, None)  # WebSocket 连接在此测试中未使用
    await server.register(bob.name, None)

    # 2. Alice 和 Bob 将密钥 Bundle 分发到服务器
    await server.distribute_key_bundle(alice.name, alice.bundle)
    await server.distribute_key_bundle(bob.name, bob.bundle)

    # 3. Alice 尝试与 Bob 建立会话
    await alice.initial_handshake(server, bob.name)

    # 4. Bob 响应 Alice 的会话请求（简化，假设 Bob 直接获取 Alice 的密钥）
    # await bob.get_key_bundle(server, alice.name)
    # await bob.initial_handshake(server, alice.name)

    # 5. Alice 计算共享密钥
    shared_secret_alice = alice.compute_shared_secret(
        identity_pri_key=alice.ipk_priv,
        signed_pri_prekey=alice.spk_priv,
        ephemeral_pri_key=alice.key_bundles[bob.name]['ephemeral_pri_key'],
        one_time_pri_prekey=None,  # 假设没有使用一次性预密钥
        identity_key_b=bob.ipk_pub,
        signed_prekey_b=bob.spk_pub,
        ephemeral_key_b=alice.key_bundles[bob.name]['ephemeral_pub_key'],
        one_time_prekey_b=None  # 假设没有使用一次性预密钥
    )

    # 6. 验证共享密钥是否为 32 字节
    assert isinstance(shared_secret_alice, bytes)
    assert len(shared_secret_alice) == 32