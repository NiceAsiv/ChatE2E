from typing import Optional, Callable
from chate2e.client.client_server import ChatClient
from chate2e.client.login_ui import LoginUI
from PyQt6.QtWidgets import QMessageBox, QApplication
from PyQt6.QtCore import QObject
from chate2e.client.models import DataManager
import sys
from PyQt6.QtCore import QObject, pyqtSignal

class LoginWindow(QObject):
    login_success = pyqtSignal(str, str)
    """登录窗口"""
    def __init__(self, chat_client: ChatClient ,data_manager: DataManager):
        super().__init__()
        self.login_window = LoginUI()
        self.chat_client = chat_client
        self.data_manager = data_manager
        self.on_login_success = None

        # 绑定信号
        self.login_window.login_clicked.connect(self._handle_login)
        self.login_window.register_clicked.connect(self._handle_register)
        
    def _handle_login(self, username: str, password: str):
        """处理登录逻辑"""
        try:
            # 验证本地密码
            uuid = self.data_manager.verify_user(username, password)
            if not uuid:
                self.login_window.show_error("错误", "用户名或密码错误")
                self.login_window.clear_password()
                return
            self.chat_client.user_id = uuid
            self.chat_client.username = username
            self.chat_client.protocol.user_id = uuid
            self.chat_client.protocol.load_signal_from_local_bundle(self.data_manager.get_local_bundle())
            self.login_success.emit(username, uuid)
        except Exception as e:
            self.login_window.show_error("错误", f"登录失败: {str(e)}")
            
    def _handle_register(self, username: str, password: str):
        """处理注册逻辑"""
        try:
            # 向服务器注册 - 使用同步方法
            if not self.chat_client.register_sync(username): 
                self.login_window.show_error(
                "错误", 
                "注册失败：无法连接到服务器，请确保服务器已启动")
                return
                
            # 保存用户信息到本地
            if self.data_manager.register_user(
                username,
                password,
                self.chat_client.user_id,
                self.chat_client.protocol.create_bundle(),
                self.chat_client.protocol.create_local_bundle()
            ):
                self.login_window.show_success("成功", "注册成功，请登录")
                self.login_window.clear_password()
            else:
                self.login_window.show_error("错误", "保存用户信息失败")
                
        except Exception as e:
            self.login_window.show_error("错误", f"注册失败: {str(e)}")
            print(e)
    
    def set_login_callback(self, callback: Callable):
        """设置登录成功回调"""
        self.on_login_success = callback
            
    def show(self):
        """显示登录窗口"""
        self.login_window.show()
        
def main():
    app = QApplication(sys.argv)
    
    # 创建登录窗口
    login_window = LoginWindow('http://localhost:5000')
    
    def on_login_success(chat_client):
        print(f"用户 {chat_client.username} 登录成功!")
        # 这里可以创建并显示主窗口
        
    login_window.set_login_callback(on_login_success)
    login_window.show()
    
    # 运行Qt事件循环
    sys.exit(app.exec())

if __name__ == '__main__':
    main()