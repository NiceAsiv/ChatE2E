from chate2e.crypto.protocol.signal_protocol import SignalProtocol


# 使用示例
async def main():
    # Create protocol instances
    alice = SignalProtocol()
    bob = SignalProtocol()

    # Initialize identities
    alice.initialize_identity("u001")
    bob.initialize_identity("u002")

    # Create bundles
    alice_bundle = alice.create_bundle()
    bob_bundle = bob.create_bundle()

    print("\n=== 密钥束信息 ===")
    print("Alice的一次性预密钥数量:", len(alice.one_time_prekeys))
    print("Bob的一次性预密钥数量:", len(bob.one_time_prekeys))

    print("Alice的初始链密钥:", alice.sending_chain_key and alice.sending_chain_key[:8].hex())
    print("Bob的初始链密钥:", bob.receiving_chain_key and bob.receiving_chain_key[:8].hex())

    print("\n=== 建立初始会话 ===")

    # Store each other's bundles
    alice.set_peer_bundle("u002", bob_bundle)
    bob.set_peer_bundle("u001", alice_bundle)

    # Alice initiates session
    init_message = alice.initiate_session(
        peer_id="u002",
        session_id="session1",
        recipient_identity_key=bob.identity_key_pub,
        recipient_signed_prekey=bob.signed_prekey_pub,
        recipient_one_time_prekey=bob.one_time_prekeys_pub[0],
        is_initiator=True
    )

    # Bob responds to session initiation
    bob.initiate_session(
        peer_id="u001",
        session_id="session1",
        recipient_identity_key=alice.identity_key_pub,
        recipient_signed_prekey=alice.signed_prekey_pub,
        recipient_ephemeral_key=alice.ephemeral_key_pub,
        own_one_time_prekey=bob.one_time_prekeys_pub[0],
        is_initiator=False
    )

    print("Alice 发送链密钥:", alice.sending_chain_key[:8].hex())
    print("Alice 接收链密钥:", alice.receiving_chain_key[:8].hex())
    print("Bob 发送链密钥:", bob.sending_chain_key[:8].hex())
    print("Bob 接收链密钥:", bob.receiving_chain_key[:8].hex())

    print("\n=== 加密和解密消息 ===")

    async def send_message(sender: SignalProtocol, receiver: SignalProtocol, message: str, round_num: int):
        print(f"\n=== 第 {round_num} 轮消息交换 ===")
        print(f"发送前链密钥: {sender.sending_chain_key[:8].hex()}")

        encrypted = sender.encrypt_message(message)
        print(f"消息已加密，新的链密钥: {sender.sending_chain_key[:8].hex()}")

        decrypted = receiver.decrypt_message(encrypted)
        print(f"消息已解密，接收方链密钥: {receiver.receiving_chain_key[:8].hex()}")

        print(f"原始消息: {message}")
        print(f"解密消息: {decrypted}")
        return encrypted, decrypted

        # 第一轮：Alice -> Bob

    await send_message(
        alice, bob,
        "Hello Bob! This is the first message in our secure chat.",
        1
    )

    # 第二轮：Bob -> Alice
    await send_message(
        bob, alice,
        "Hi Alice! Received your message. This is my response.",
        2
    )

    # 第三轮：Alice -> Bob
    await send_message(
        alice, bob,
        "Great! The double ratchet is working. Here's another message.",
        3
    )

    # 第四轮：Bob -> Alice
    await send_message(
        bob, alice,
        "Perfect! Each message gets a new chain key for perfect forward secrecy.",
        4
    )

    print("\n=== 最终密钥状态 ===")
    print("Alice发送链密钥:", alice.sending_chain_key[:8].hex())
    print("Bob接收链密钥:", bob.receiving_chain_key[:8].hex())
    print("Alice接收链密钥:", alice.receiving_chain_key[:8].hex())
    print("Bob发送链密钥:", bob.sending_chain_key[:8].hex())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())