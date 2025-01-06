import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

class LoginWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 加载UI文件
        uic.loadUi('./login.ui', self)
        
        # 设置窗口属性
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)  # 无边框窗口
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 透明背景
        
        # 获取UI元素
        self.closeButton = self.findChild(QtWidgets.QPushButton, 'closeButton')
        self.avatarLabel = self.findChild(QtWidgets.QLabel, 'avatarLabel')
        self.usernameEdit = self.findChild(QtWidgets.QLineEdit, 'usernameEdit')
        self.passwordEdit = self.findChild(QtWidgets.QLineEdit, 'passwordEdit')
        self.loginButton = self.findChild(QtWidgets.QPushButton, 'loginButton')
        self.rememberPwdCheck = self.findChild(QtWidgets.QCheckBox, 'rememberPwdCheck')
        self.autoLoginCheck = self.findChild(QtWidgets.QCheckBox, 'autoLoginCheck')
        self.registerLink = self.findChild(QtWidgets.QLabel, 'registerLink')
        self.forgotPwdLink = self.findChild(QtWidgets.QLabel, 'forgotPwdLink')
        
        # 设置QQ企鹅头像
        penguin_pixmap = QPixmap('penguin.png')
        self.avatarLabel.setPixmap(penguin_pixmap.scaled(
            100, 100, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))
        
        # 设置背景图片
        background_pixmap = QPixmap('background.jpg')
        self.findChild(QtWidgets.QLabel, 'backgroundLabel').setPixmap(
            background_pixmap.scaled(
                400, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )
        
        # 连接信号和槽
        self.loginButton.clicked.connect(self.handle_login)
        self.rememberPwdCheck.stateChanged.connect(self.handle_remember_pwd)
        self.autoLoginCheck.stateChanged.connect(self.handle_auto_login)
        
        # 设置鼠标跟踪，用于实现窗口拖动
        self.old_pos = None
        self.pressing = False
        
    def handle_login(self):
        username = self.usernameEdit.text()
        password = self.passwordEdit.text()
        
        # 这里添加登录验证逻辑
        print(f"Login attempt - Username: {username}, Password: {password}")
        
        # 登录成功后可以关闭登录窗口，打开主聊天窗口
        # self.close()
        # self.chat_window = ChatWindow()
        # self.chat_window.show()
        
    def handle_remember_pwd(self, state):
        # 处理"记住密码"复选框状态变化
        if state == Qt.CheckState.Checked.value:
            print("Remember password enabled")
        else:
            print("Remember password disabled")
            
    def handle_auto_login(self, state):
        # 处理"自动登录"复选框状态变化
        if state == Qt.CheckState.Checked.value:
            print("Auto login enabled")
        else:
            print("Auto login disabled")
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressing = True
            self.old_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.pressing = False
            self.old_pos = None

    def mouseMoveEvent(self, event):
        if self.pressing and self.old_pos:
            delta = event.pos() - self.old_pos
            self.move(self.pos() + delta)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())