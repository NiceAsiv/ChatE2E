import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                           QVBoxLayout, QListWidget, QListWidgetItem, QLabel, 
                           QLineEdit, QPushButton, QScrollArea)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap

class ChatItem(QWidget):
    def __init__(self, avatar_path, username, message, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        
        # Avatar
        avatar_label = QLabel()
        pixmap = QPixmap(avatar_path).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio)
        avatar_label.setPixmap(pixmap)
        avatar_label.setFixedSize(40, 40)
        
        # Message content
        msg_layout = QVBoxLayout()
        username_label = QLabel(username)
        username_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        message_label = QLabel(message)
        message_label.setStyleSheet("color: #FFFFFF;")
        msg_layout.addWidget(username_label)
        msg_layout.addWidget(message_label)
        
        layout.addWidget(avatar_label)
        layout.addLayout(msg_layout)
        layout.addStretch()
        self.setLayout(layout)

class UserListItem(QWidget):
    def __init__(self, avatar_path, username, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()
        
        # Avatar
        avatar_label = QLabel()
        pixmap = QPixmap(avatar_path).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio)
        avatar_label.setPixmap(pixmap)
        avatar_label.setFixedSize(32, 32)
        
        # Username
        username_label = QLabel(username)
        username_label.setStyleSheet("color: #FFFFFF;")
        
        layout.addWidget(avatar_label)
        layout.addWidget(username_label)
        layout.addStretch()
        self.setLayout(layout)

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("聊天室")
        self.setMinimumSize(1200, 800)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Left sidebar (Channel list)
        left_sidebar = QWidget()
        left_sidebar.setFixedWidth(200)
        left_sidebar.setStyleSheet("background-color: #2B2B2B;")
        left_layout = QVBoxLayout(left_sidebar)
        
        # Channel header
        channel_header = QLabel("大哲聊")
        channel_header.setStyleSheet("color: #FFFFFF; font-size: 18px; padding: 10px;")
        left_layout.addWidget(channel_header)
        
        # Channel list
        channel_list = QListWidget()
        channel_list.setStyleSheet("""
            QListWidget {
                background-color: #2B2B2B;
                border: none;
            }
            QListWidget::item {
                padding: 5px;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
        """)
        left_layout.addWidget(channel_list)
        
        # Main chat area
        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_widget.setStyleSheet("background-color: #363636;")
        
        # Chat header
        chat_header = QLabel("居然还有威望")
        chat_header.setStyleSheet("color: #FFFFFF; font-size: 16px; padding: 10px;")
        chat_layout.addWidget(chat_header)
        
        # Chat messages area
        messages_area = QListWidget()
        messages_area.setStyleSheet("""
            QListWidget {
                background-color: #363636;
                border: none;
            }
        """)
        chat_layout.addWidget(messages_area)
        
        # Input area
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        
        # Message input
        message_input = QLineEdit()
        message_input.setPlaceholderText("聊聊点什么吧~")
        message_input.setStyleSheet("""
            QLineEdit {
                background-color: #2B2B2B;
                border: 1px solid #404040;
                border-radius: 4px;
                color: #FFFFFF;
                padding: 8px;
            }
        """)
        
        # Send button
        send_button = QPushButton()
        send_button.setIcon(QIcon("path_to_send_icon.png"))
        send_button.setFixedSize(32, 32)
        
        input_layout.addWidget(message_input)
        input_layout.addWidget(send_button)
        chat_layout.addWidget(input_widget)
        
        # Right sidebar (User list)
        right_sidebar = QWidget()
        right_sidebar.setFixedWidth(200)
        right_sidebar.setStyleSheet("background-color: #2B2B2B;")
        right_layout = QVBoxLayout(right_sidebar)
        
        # User list header
        user_header = QLabel("群成员(7/53)")
        user_header.setStyleSheet("color: #FFFFFF; font-size: 14px; padding: 10px;")
        right_layout.addWidget(user_header)
        
        # User list
        user_list = QListWidget()
        user_list.setStyleSheet("""
            QListWidget {
                background-color: #2B2B2B;
                border: none;
            }
        """)
        right_layout.addWidget(user_list)
        
        # Add sample users
        sample_users = ["少年阿磊", "云舒", "名字过长10604", "可乐", "z龙"]
        for user in sample_users:
            item = QListWidgetItem(user_list)
            user_widget = UserListItem("path_to_avatar.png", user)
            item.setSizeHint(user_widget.sizeHint())
            user_list.setItemWidget(item, user_widget)
        
        # Add sample messages
        sample_messages = [
            ("统一牛奶", "牛哥"),
            ("统一牛奶", "能换大米吗"),
            ("高级牛奶", "兄弟们点点赞，给大家看照片"),
        ]
        for avatar, msg in sample_messages:
            item = QListWidgetItem(messages_area)
            message_widget = ChatItem("path_to_avatar.png", avatar, msg)
            item.setSizeHint(message_widget.sizeHint())
            messages_area.setItemWidget(item, message_widget)
        
        # Add everything to main layout
        main_layout.addWidget(left_sidebar)
        main_layout.addWidget(chat_widget)
        main_layout.addWidget(right_sidebar)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #363636;
            }
        """)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())