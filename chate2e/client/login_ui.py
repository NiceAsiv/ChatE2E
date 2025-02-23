from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon

class LoginUI(QWidget):
    login_clicked = pyqtSignal(str, str)
    register_clicked = pyqtSignal(str, str)
    
    def __init__(self):
        super().__init__()
        self.dragPosition = QPoint()
        self.init_ui()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 500)  # 设置固定窗口大小
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部布局
        top_layout = QHBoxLayout()
        
        # 添加标题
        title_label = QLabel("用户登录")
        title_label.setObjectName("titleLabel")
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton()
        close_btn.setFixedSize(30, 30)
        #调整按钮图标大小
        close_btn.setIconSize(QSize(20, 20))
        close_btn.setIcon(QIcon("assets/icons/close.png"))
        close_btn.setObjectName("closeButton")
        close_btn.clicked.connect(self.close)
        top_layout.addWidget(close_btn)
        
        # Logo/图标
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/icons/logo.png")
        logo_label.setPixmap(logo_pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 输入区域
        input_layout = QVBoxLayout()
        input_layout.setSpacing(20)
        
        # 用户名输入框
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("用户名")
        self.username_edit.setObjectName("inputEdit")
        self.username_edit.setFixedHeight(40)
        
        # 密码输入框
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setObjectName("inputEdit")
        self.password_edit.setFixedHeight(40)
        
        input_layout.addWidget(self.username_edit)
        input_layout.addWidget(self.password_edit)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.login_btn = QPushButton("登录")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.setFixedHeight(40)
        
        self.register_btn = QPushButton("注册")
        self.register_btn.setObjectName("registerButton")
        self.register_btn.setFixedHeight(40)

        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)
        
        # 绑定事件
        self.login_btn.clicked.connect(self._handle_login_click)
        self.register_btn.clicked.connect(self._handle_register_click)
        self.password_edit.returnPressed.connect(self._handle_login_click)
        
        # 组装布局
        layout.addLayout(top_layout)
        layout.addWidget(logo_label)
        layout.addSpacing(30)
        layout.addLayout(input_layout)
        layout.addSpacing(20)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                font-family: "Microsoft YaHei UI";
            }
            #titleLabel {
                color: #333333;
                font-size: 18px;
                font-weight: bold;
            }
            #inputEdit {
                border: 1px solid #CCCCCC;
                border-radius: 20px;
                padding: 0 15px;
                font-size: 14px;
                background-color: #F5F5F5;
            }
            #inputEdit:focus {
                border-color: #2B5278;
                background-color: #FFFFFF;
            }
            #loginButton {
                background-color: #2B5278;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }
            #loginButton:hover {
                background-color: #1A365D;
            }
            #registerButton {
                background-color: transparent;
                color: #2B5278;
                border: 1px solid #2B5278;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }
            #registerButton:hover {
                background-color: #F0F0F0;
            }
            #closeButton {
                background-color: transparent;
                border: none;
            }
            #closeButton:hover {
                background-color: #FF4444;
            }
        """)
        
    def paintEvent(self, event):
        """绘制背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制圆角矩形
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 10, 10)
        
        # 绘制背景图片
        background = QPixmap("assets/background/login.jpg")
        if not background.isNull():
            painter.setOpacity(0.1)
            painter.drawPixmap(self.rect(), background)
            
    def mousePressEvent(self, event):
        """实现窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPosition = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """实现窗口拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPosition)
    def show_error(self, title: str, message: str):
        """显示错误消息"""
        QMessageBox.warning(self, title, message)

    def show_success(self, title: str, message: str):
        """显示成功消息"""
        QMessageBox.information(self, title, message)
        
    def _handle_login_click(self):
        """处理登录按钮点击"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return
            
        self.login_clicked.emit(username, password)
        
    def _handle_register_click(self):
        """处理注册按钮点击"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return
            
        if len(password) < 6:
            QMessageBox.warning(self, "提示", "密码长度至少6位")
            return
            
        self.register_clicked.emit(username, password)
        
    def clear_password(self):
        """清空密码输入框"""
        self.password_edit.clear()