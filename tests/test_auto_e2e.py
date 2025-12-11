"""
自动化E2E消息测试 - 无需UI
测试Alice和Bob之间的完整加密消息传递
"""
import os
import sys
import time
import shutil
import threading

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from chate2e.client.client_server import ChatClient
from chate2e.client.models import DataManager, UserProfile, UserStatus
from chate2e.model.message import Message, MessageType

class TestUser:
    """测试用户类"""
    def __init__(self, username: str, server_url: str = "http://localhost:5000"):
        self.username = username
        self.server_url = server_url
        self.received_messages = []
        
        # 初始化数据管理器
        data_dir = os.path.join(project_root, 'chate2e', 'client', 'chat_data')
        self.data_manager = DataManager(data_dir)
        
        # 初始化客户端
        self.client = ChatClient(server_url, self.data_manager)
        
        # 注册消息处理器
        self.client.register_message_handler(self._on_message)
        
    def _on_message(self, message: Message):
        """消息处理回调"""
        try:
            decrypted = self.client.protocol.decrypt_message(message)
            print(f"[{self.username}] 📨 收到消息: {decrypted}")
            self.received_messages.append(decrypted)
        except Exception as e:
            print(f"[{self.username}] ❌ 解密失败: {e}")
    
    def register(self):
        """注册用户"""
        print(f"[{self.username}] 注册中...")
        if self.client.register_sync(self.username):
            # 设置数据管理器
            self.data_manager.user_id = self.client.user_id
            self.data_manager.useruuid = self.client.user_id
            self.data_manager.user_data_dir = os.path.join(
                self.data_manager.base_dir, self.client.user_id
            )
            os.makedirs(self.data_manager.user_data_dir, exist_ok=True)
            
            self.data_manager.user_file = os.path.join(
                self.data_manager.user_data_dir, "user_profile.json"
            )
            self.data_manager.sessions_file = os.path.join(
                self.data_manager.user_data_dir, "chat_sessions.json"
            )
            
            # 加载或创建用户数据
            self.data_manager.load_data()
            if not self.data_manager.user:
                self.data_manager.user = UserProfile(
                    user_id=self.client.user_id,
                    username=self.username,
                    avatar_path='',
                    status=UserStatus.ONLINE
                )
                self.data_manager.save_data()
            
            print(f"[{self.username}] ✓ 注册成功 (ID: {self.client.user_id})")
            return True
        else:
            print(f"[{self.username}] ✗ 注册失败")
            return False
    
    def connect(self):
        """连接到服务器"""
        print(f"[{self.username}] 连接服务器...")
        try:
            self.client.connect_sync()
            print(f"[{self.username}] ✓ 已连接")
            return True
        except Exception as e:
            print(f"[{self.username}] ✗ 连接失败: {e}")
            return False
    
    def init_session_with(self, peer_id: str):
        """初始化与对方的会话"""
        print(f"[{self.username}] 初始化与 {peer_id} 的会话...")
        session = self.data_manager.get_or_create_session(peer_id)
        if self.client.init_session_sync(peer_id, session.session_id):
            print(f"[{self.username}] ✓ 会话初始化成功")
            return session.session_id
        else:
            print(f"[{self.username}] ✗ 会话初始化失败")
            return None
    
    def send_message(self, peer_id: str, text: str):
        """发送消息"""
        print(f"[{self.username}] 发送消息给 {peer_id}: '{text}'")
        try:
            encrypted_msg = self.client.protocol.encrypt_message(text)
            if self.client.send_message_sync(peer_id, encrypted_msg):
                print(f"[{self.username}] ✓ 消息已发送")
                return True
            else:
                print(f"[{self.username}] ✗ 消息发送失败")
                return False
        except Exception as e:
            print(f"[{self.username}] ✗ 发送异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def disconnect(self):
        """断开连接"""
        self.client.disconnect_sync()
        print(f"[{self.username}] 已断开连接")
    
    def cleanup(self):
        """清理用户数据"""
        if os.path.exists(self.data_manager.user_data_dir):
            shutil.rmtree(self.data_manager.user_data_dir)
            print(f"[{self.username}] 已清理数据")


def test_e2e_messaging():
    """完整的E2E消息测试"""
    print("=" * 70)
    print("🚀 开始E2E加密消息测试")
    print("=" * 70)
    
    # 创建两个测试用户
    alice = TestUser(f"alice_{int(time.time())}")
    bob = TestUser(f"bob_{int(time.time())}")
    
    try:
        # 1. 注册
        print("\n📝 步骤1: 注册用户")
        if not alice.register() or not bob.register():
            print("❌ 注册失败")
            return False
        
        # 2. 连接
        print("\n🔌 步骤2: 连接服务器")
        if not alice.connect() or not bob.connect():
            print("❌ 连接失败")
            return False
        
        time.sleep(2)  # 等待连接稳定
        
        # 3. Alice初始化会话
        print("\n🔐 步骤3: 初始化加密会话")
        session_id = alice.init_session_with(bob.client.user_id)
        if not session_id:
            print("❌ 会话初始化失败")
            return False
        
        time.sleep(2)  # 等待会话建立
        
        # 检查会话状态
        print(f"\n📊 会话状态检查:")
        print(f"  Alice session_initialized: {alice.client.protocol.session_initialized}")
        print(f"  Bob session_initialized: {bob.client.protocol.session_initialized}")
        
        if not alice.client.protocol.session_initialized:
            print("❌ Alice会话未初始化")
            return False
        
        if not bob.client.protocol.session_initialized:
            print("❌ Bob会话未初始化")
            return False
        
        # 4. Alice发送消息给Bob
        print("\n💬 步骤4: Alice → Bob")
        alice.send_message(bob.client.user_id, "Hello Bob! 你好！")
        time.sleep(2)
        
        # 5. Bob发送消息给Alice
        print("\n💬 步骤5: Bob → Alice")
        bob.send_message(alice.client.user_id, "Hi Alice! 收到了！")
        time.sleep(2)
        
        # 6. Alice再发一条
        print("\n💬 步骤6: Alice → Bob (第二条)")
        alice.send_message(bob.client.user_id, "Great! 测试成功！")
        time.sleep(2)
        
        # 7. 检查收到的消息
        print("\n📬 步骤7: 检查接收结果")
        print(f"  Bob收到消息数: {len(bob.received_messages)}")
        for i, msg in enumerate(bob.received_messages, 1):
            print(f"    {i}. {msg}")
        
        print(f"  Alice收到消息数: {len(alice.received_messages)}")
        for i, msg in enumerate(alice.received_messages, 1):
            print(f"    {i}. {msg}")
        
        # 验证结果
        success = len(bob.received_messages) >= 2 and len(alice.received_messages) >= 1
        
        if success:
            print("\n" + "=" * 70)
            print("✅ 测试成功！所有消息正确加密和解密")
            print("=" * 70)
        else:
            print("\n" + "=" * 70)
            print("❌ 测试失败：消息接收不完整")
            print("=" * 70)
        
        return success
        
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理
        print("\n🧹 清理测试数据...")
        alice.disconnect()
        bob.disconnect()
        time.sleep(1)
        alice.cleanup()
        bob.cleanup()


if __name__ == "__main__":
    success = test_e2e_messaging()
    sys.exit(0 if success else 1)
