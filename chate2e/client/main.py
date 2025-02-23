import sys

from PyQt6.QtWidgets import QApplication

from chate2e.client.chat_logic import ChatWindow
from chate2e.client.client_server import ChatClient
from chate2e.client.login_logic import LoginWindow
from chate2e.client.models import DataManager


class ChatApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.login_window = None
        self.chat_window = None
        self.server_url = "http://localhost:5000"
        self.data_manager = DataManager(None)
        self.server = ChatClient(self.server_url, self.data_manager)

    def run(self):
        # 创建并显示登录窗口
        self.login_window = LoginWindow(self.server, self.data_manager)
        self.login_window.login_success.connect(self.on_login_success)
        self.login_window.show()
        
        return self.app.exec()

    def on_login_success(self, username: str , user_id: str):
        """处理登录成功事件"""
        print(f"用户 {username} 登录成功")
        print(self.server.user_id == user_id)
        try :
            if self.server.connect_sync():
                print("连接服务器成功")
                # 关闭登录窗口
                self.login_window.login_window.close()
                self.chat_window = ChatWindow(username, self.server, self.data_manager)
                self.chat_window.show()

        except Exception as e:
            print(f"连接服务器失败: {e}")
            return


        
if __name__ == "__main__":
    app = ChatApp()
    sys.exit(app.run())