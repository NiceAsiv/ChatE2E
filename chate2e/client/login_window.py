from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """初始化登录界面"""
        # 设置窗口属性
        self.setWindowTitle("端到端通信客户端")
        self.setFixedSize(800, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # 无边框
        
        # 主布局
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        
        # 左侧图片区域
        left_widget = QWidget()
        left_widget.setFixedWidth(400)
        left_layout = QVBoxLayout(left_widget)
        
        # 添加logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/logo.png")
        logo_label.setPixmap(logo_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio))
        left_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 添加欢迎文本
        welcome_label = QLabel("欢迎使用\n端到端通信客户端")
        welcome_label.setFont(QFont("Microsoft YaHei UI", 20))
        welcome_label.setStyleSheet("color: #2B5278;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(welcome_label)
        
        main_layout.addWidget(left_widget)
        
        # 右侧登录区域
        right_widget = QWidget()
        right_widget.setFixedWidth(400)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(20)
        
        # 登录表单
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        
        # 用户名输入框
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.setFixedHeight(40)
        
        # 密码输入框
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setFixedHeight(40)
        
        # 登录按钮
        self.login_btn = QPushButton("登录")
        self.login_btn.setFixedHeight(40)
        
        # 注册按钮
        self.register_btn = QPushButton("注册新账号")
        self.register_btn.setFixedHeight(40)
        
        # 添加到表单布局
        form_layout.addWidget(self.username_edit)
        form_layout.addWidget(self.password_edit)
        form_layout.addWidget(self.login_btn)
        form_layout.addWidget(self.register_btn)
        
        right_layout.addStretch()
        right_layout.addWidget(form_widget)
        right_layout.addStretch()
        
        main_layout.addWidget(right_widget)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                font-family: "Microsoft YaHei UI";
            }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 20px;
                padding: 0 15px;
                font-size: 14px;
                background-color: #F5F5F5;
            }
            QLineEdit:focus {
                border-color: #2B5278;
                background-color: #FFFFFF;
            }
            QPushButton {
                background-color: #2B5278;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1A365D;
            }
            #register_btn {
                background-color: transparent;
                color: #2B5278;
                border: 1px solid #2B5278;
            }
            #register_btn:hover {
                background-color: #F0F0F0;
            }
        """)

    def paintEvent(self, event):
        """绘制背景图片"""
        painter = QPainter(self)
        
        # 尝试加载背景图片
        background_image = QPixmap("assets/login_background.jpg")
        if background_image.isNull():
            # 尝试其他可能的路径
            alternative_paths = [
                "./assets/login_background.jpg",
                "../assets/login_background.jpg",
                "../../assets/login_background.jpg",
            ]
            
            for path in alternative_paths:
                background_image = QPixmap(path)
                if not background_image.isNull():
                    break
                    
            # 如果仍然无法加载，使用纯色背景
            if background_image.isNull():
                painter.fillRect(self.rect(), QColor("#F5F5F5"))
                print("警告: 无法加载背景图片，使用默认背景色")
                return
        
        painter.setOpacity(0.1)  # 设置背景图透明度
        painter.drawPixmap(self.rect(), background_image)
        
    def mousePressEvent(self, event):
        """实现窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPosition = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """实现窗口拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPosition)
            
def main():
    app = QApplication([])
    login_window = LoginWindow()
    login_window.show()
    app.exec()
        
if __name__ == '__main__':
        main()