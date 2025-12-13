from PyQt6.QtWidgets import (QWidget, QHBoxLayout,
                             QVBoxLayout, QListWidget, QLabel,
                             QLineEdit, QPushButton, QMainWindow,
                             QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
                             QFileDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
import os
import qtawesome as qta

# 获取客户端目录的绝对路径
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_AVATAR_PATH = os.path.join(CLIENT_DIR, "assets", "avatars", "default.png")


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
        
        if is_sender:
            bg_color = '#2B5278'
            text_color = '#FFFFFF'
            radius_style = 'border-top-right-radius: 2px;'
            user_text_color = '#E5E7EB'
        else:
            bg_color = '#FFFFFF'
            text_color = '#1F2937'
            radius_style = 'border-top-left-radius: 2px;'
            user_text_color = '#6B7280'

        msg_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 12px;
                {radius_style}
                padding: 10px 14px;
            }}
        """)
        msg_layout = QVBoxLayout(msg_widget)

        username_label = QLabel(username)
        username_label.setStyleSheet(f"""
            color: {user_text_color};
            font-weight: 600;
            font-size: 11px;
            margin-bottom: 2px;
        """)

        message_label = QLabel(message)
        message_label.setStyleSheet(f"color: {text_color}; font-size: 14px; line-height: 1.4;")
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
        self.setFixedHeight(70)  # 固定高度，防止被压缩
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10) # 增加内边距
        layout.setSpacing(12) # 增加头像和文字的间距

        # Avatar
        avatar = AvatarLabel(44) # 稍微调大头像
        avatar.set_avatar(avatar_path)

        # User info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 2, 0, 2) # 微调文字垂直位置
        
        username_label = QLabel(username)
        username_label.setStyleSheet("""
            color: #1F2937;
            font-weight: 600;
            font-size: 15px;
            font-family: "Segoe UI", "Microsoft YaHei";
        """)
        
        last_message_label = QLabel(last_message or "暂无消息")
        last_message_label.setStyleSheet("""
            color: #9CA3AF;
            font-size: 13px;
            font-family: "Segoe UI", "Microsoft YaHei";
        """)
        
        info_layout.addWidget(username_label)
        info_layout.addWidget(last_message_label)
        info_layout.addStretch() # 确保文字靠上对齐

        # Status indicator
        status_container = QVBoxLayout()
        status_container.setContentsMargins(0, 4, 0, 0)
        status_label = QLabel("●")
        status_label.setStyleSheet(f"""
            color: {'#10B981' if status == 'online' else '#D1D5DB'};
            font-size: 10px;
        """)
        status_container.addWidget(status_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        status_container.addStretch()

        layout.addWidget(avatar)
        layout.addLayout(info_layout)
        layout.addLayout(status_container)
        
        self.setLayout(layout)


class CurrentUserWidget(QWidget):
    """当前用户信息组件"""
    def __init__(self, avatar_path, username, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 20, 20, 10)
        layout.setSpacing(15)

        # Avatar
        avatar = AvatarLabel(48)
        avatar.set_avatar(avatar_path)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(username)
        name_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #111827;
            font-family: "Segoe UI", "Microsoft YaHei";
        """)
        
        status_label = QLabel("在线")
        status_label.setStyleSheet("""
            color: #10B981;
            font-size: 12px;
            font-weight: 500;
        """)
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(status_label)
        
        layout.addWidget(avatar)
        layout.addLayout(info_layout)
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
                background-color: #F3F4F6;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 20px;
                padding: 8px 16px;
                color: #1F2937;
            }
            QLineEdit:focus {
                border: 1px solid #2B5278;
            }
            QPushButton {
                background-color: #2B5278;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1E3A5F;
            }
            QPushButton:pressed {
                background-color: #172E4D;
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
                border-right: 1px solid #E5E7EB;
            }
        """)
        left_layout = QVBoxLayout(left_sidebar)

        # 用户信息
        # self.user_info = None  # 预留位置，在client_logic中填充
        # 使用 CurrentUserWidget 作为占位符，逻辑层可以替换或更新它
        # 注意：逻辑层可能需要修改以适配新的 CurrentUserWidget
        self.user_info_container = QWidget()
        self.user_info_layout = QVBoxLayout(self.user_info_container)
        self.user_info_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.user_info_container)

        # 搜索框
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索联系人...")
        search_input.addAction(qta.icon('fa5s.search', color='#9CA3AF'), QLineEdit.ActionPosition.LeadingPosition)
        search_input.setStyleSheet("""
            QLineEdit {
                background-color: #F3F4F6;
                border: 1px solid transparent;
                border-radius: 8px;
                padding: 8px 12px;
                padding-left: 32px;
                margin: 12px 8px;
                color: #1F2937;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 1px solid #2B5278;
            }
        """)
        left_layout.addWidget(search_input)

        # 联系人列表
        self.contact_list = QListWidget()
        self.contact_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 12px;
                margin: 4px 8px;
                border-radius: 8px;
                color: #1F2937;
            }
            QListWidget::item:selected {
                background-color: #EFF6FF;
            }
            QListWidget::item:hover {
                background-color: #F9FAFB;
            }
        """)
        left_layout.addWidget(self.contact_list)

        # 添加联系人按钮
        self.add_contact_btn = QPushButton("添加联系人")
        self.add_contact_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                border: none;
                border-radius: 8px;
                color: white;
                padding: 10px;
                margin: 8px 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1E3A5F;
            }
            QPushButton:pressed {
                background-color: #172E4D;
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
        input_container = QWidget()
        input_container.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-top: 1px solid #E5E7EB;
            }
        """)
        input_container.setFixedHeight(80) # 固定高度
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(20, 10, 20, 10)
        input_layout.setSpacing(10)

        # 文件上传按钮
        self.upload_btn = QPushButton()
        self.upload_btn.setIcon(qta.icon('fa5s.paperclip', color='#6B7280'))
        self.upload_btn.setFixedSize(40, 40)
        self.upload_btn.setIconSize(QSize(20, 20))
        self.upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.upload_btn.setToolTip("发送文件")
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #F3F4F6;
            }
        """)
        input_layout.addWidget(self.upload_btn)

        # 消息输入框
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入消息...")
        self.message_input.setStyleSheet("""
            QLineEdit {
                background-color: #F9FAFB;
                border: 1px solid #E5E7EB;
                border-radius: 20px;
                padding: 10px 20px;
                font-size: 14px;
                color: #1F2937;
            }
            QLineEdit:focus {
                background-color: #FFFFFF;
                border: 1px solid #2B5278;
            }
        """)
        input_layout.addWidget(self.message_input)

        # 发送按钮
        self.send_btn = QPushButton()
        self.send_btn.setIcon(qta.icon('fa5s.paper-plane', color='#FFFFFF')) # 白色图标
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setIconSize(QSize(16, 16))
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setToolTip("发送消息")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                border: none;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #1E3A5F;
            }
            QPushButton:pressed {
                background-color: #172E4D;
            }
        """)
        input_layout.addWidget(self.send_btn)

        # 将输入区域添加到聊天布局
        chat_layout.addWidget(input_container)

        # 添加所有部分到主布局
        main_layout.addWidget(left_sidebar)
        main_layout.addWidget(chat_widget)

        self.left_layout = left_layout