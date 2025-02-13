# filepath: /e:/code/lesson/ChatE2E/chate2e/client/ui.py
from PyQt6.QtWidgets import (QWidget, QHBoxLayout,
                             QVBoxLayout, QListWidget, QLabel,
                             QLineEdit, QPushButton, QMainWindow,
                             QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
                             QFileDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap

DEFAULT_AVATAR_PATH = "assets/avatars/default.png"


class AvatarLabel(QLabel):
    """头像标签类，处理圆形头像显示和默认头像"""

    def __init__(self, size, parent=None):
        super().__init__(parent)
        self.size = size
        self.setFixedSize(size, size)
        self.setScaledContents(True)

    def set_avatar(self, avatar_path=None):
        """设置头像图片"""
        # 如果未提供头像路径或头像路径为空字符串，使用默认头像
        if not avatar_path or avatar_path.strip() == "":
            avatar_path = DEFAULT_AVATAR_PATH

        pixmap = QPixmap(avatar_path)
        if pixmap.isNull():
            # 如果无法加载指定头像，使用默认头像
            print(f"无法加载头像: {avatar_path}，使用默认头像")
            pixmap = QPixmap(DEFAULT_AVATAR_PATH)
            if pixmap.isNull():
                print("无法加载默认头像")
                return

        scaled_pixmap = pixmap.scaled(
            self.size, self.size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)


class ChatItem(QWidget):
    def __init__(self, avatar_path, username, message, is_sender=False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()

        # Avatar
        avatar = AvatarLabel(40)
        avatar.set_avatar(avatar_path)

        # Message content
        msg_widget = QWidget()
        msg_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {'#DCF8C6' if is_sender else '#FFFFFF'};
                border-radius: 10px;
                padding: 8px;
            }}
        """)
        msg_layout = QVBoxLayout(msg_widget)

        username_label = QLabel(username)
        username_label.setStyleSheet("""
            color: #2B5278;
            font-weight: bold;
            font-size: 12px;
        """)

        message_label = QLabel(message)
        message_label.setStyleSheet("color: #1A1A1A;")
        message_label.setWordWrap(True)

        msg_layout.addWidget(username_label)
        msg_layout.addWidget(message_label)
        msg_layout.setSpacing(4)

        if is_sender:
            layout.addStretch()
            layout.addWidget(msg_widget)
            layout.addWidget(avatar)
        else:
            layout.addWidget(avatar)
            layout.addWidget(msg_widget)
            layout.addStretch()

        self.setLayout(layout)


class ContactItem(QWidget):
    def __init__(self, avatar_path, username, last_message="", status="offline", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()

        # Avatar
        avatar = AvatarLabel(32)
        avatar.set_avatar(avatar_path)

        # User info
        info_layout = QVBoxLayout()
        username_label = QLabel(username)
        username_label.setStyleSheet("""
            color: #1A1A1A;
            font-weight: bold;
            font-size: 14px;
        """)
        last_message_label = QLabel(last_message or "暂无消息")
        last_message_label.setStyleSheet("""
            color: #666666;
            font-size: 12px;
        """)
        info_layout.addWidget(username_label)
        info_layout.addWidget(last_message_label)

        # Status indicator
        status_label = QLabel("●")
        status_label.setStyleSheet(f"""
            color: {'#4CAF50' if status == 'online' else '#757575'};
            font-size: 10px;
        """)

        layout.addWidget(avatar)
        layout.addLayout(info_layout)
        layout.addWidget(status_label)
        layout.addStretch()
        self.setLayout(layout)


class ChatWindowUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("端到端聊天")
        self.setMinimumSize(1000, 800)

        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 20px;
                padding: 8px 16px;
                color: #1A1A1A;
            }
            QPushButton {
                background-color: #2B5278;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1A365D;
            }
        """)

        # 设置主窗口
        self.setup_ui()

    def setup_ui(self):
        """设置UI布局"""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # 左侧边栏（联系人列表）
        left_sidebar = QWidget()
        left_sidebar.setFixedWidth(300)
        left_sidebar.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-right: 1px solid #E0E0E0;
            }
        """)
        left_layout = QVBoxLayout(left_sidebar)

        # 用户信息
        self.user_info = None  # 预留位置，在client_logic中填充

        # 搜索框
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索联系人...")
        search_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                margin: 8px 0;
                color: #1A1A1A;
            }
        """)
        left_layout.addWidget(search_input)

        # 联系人列表
        self.contact_list = QListWidget()
        self.contact_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #F0F0F0;
                border-radius: 8px;
            }
            QListWidget::item:hover {
                background-color: #F5F5F5;
                border-radius: 8px;
            }
        """)
        left_layout.addWidget(self.contact_list)

        # 添加联系人按钮
        self.add_contact_btn = QPushButton("添加联系人")
        self.add_contact_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                border: none;
                border-radius: 20px;
                color: white;
                padding: 10px;
                margin: 8px 0;
            }
            QPushButton:hover {
                background-color: #1A365D;
            }
        """)
        left_layout.addWidget(self.add_contact_btn)

        # 聊天区域
        chat_widget = QWidget()
        chat_widget.setStyleSheet("background-color: #F5F5F5;")
        chat_layout = QVBoxLayout(chat_widget)

        # 聊天标题栏
        self.chat_header = QLabel("选择联系人开始聊天")
        self.chat_header.setStyleSheet("""
            background-color: #FFFFFF;
            color: #1A1A1A;
            font-size: 16px;
            font-weight: bold;
            padding: 16px;
            border-bottom: 1px solid #E0E0E0;
        """)
        chat_layout.addWidget(self.chat_header)

        # 消息区域
        self.messages_area = QListWidget()
        self.messages_area.setStyleSheet("""
            QListWidget {
                background-color: #F5F5F5;
                border: none;
                padding: 8px;
            }
        """)
        chat_layout.addWidget(self.messages_area)

        # 输入区域
        input_widget = QWidget()
        input_widget.setStyleSheet("background-color: #FFFFFF;")
        input_layout = QHBoxLayout(input_widget)

        # 文件上传按钮
        self.upload_btn = QPushButton()
        self.upload_btn.setIcon(QIcon("assets/icons/upload.png"))
        self.upload_btn.setFixedSize(40, 40)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        input_layout.addWidget(self.upload_btn)

        # 消息输入框
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #F5F5F5;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                margin: 8px;
                font-size: 14px;
            }
        """)
        input_layout.addWidget(self.message_input)

        # 发送按钮
        self.send_btn = QPushButton()
        self.send_btn.setIcon(QIcon("assets/icons/send.png"))
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        input_layout.addWidget(self.send_btn)

        # 将输入区域添加到聊天布局
        chat_layout.addWidget(input_widget)

        # 添加所有部分到主布局
        main_layout.addWidget(left_sidebar)
        main_layout.addWidget(chat_widget)

        self.left_layout = left_layout