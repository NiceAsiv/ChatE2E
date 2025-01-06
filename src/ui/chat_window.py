import sys
from PyQt6 import QtWidgets, uic
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

class ChatWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 加载UI文件
        uic.loadUi('./chat_window.ui', self)
        
        # 获取UI元素的引用
        self.messageInput = self.findChild(QtWidgets.QLineEdit, 'messageInput')
        self.sendButton = self.findChild(QtWidgets.QPushButton, 'sendButton')
        self.messageArea = self.findChild(QtWidgets.QListWidget, 'messageArea')
        self.memberList = self.findChild(QtWidgets.QListWidget, 'memberList')
        self.channelList = self.findChild(QtWidgets.QListWidget, 'channelList')
        
        # 设置发送按钮图标
        self.sendButton.setIcon(QIcon("path_to_send_icon.png"))
        
        # 连接信号和槽
        self.sendButton.clicked.connect(self.send_message)
        self.messageInput.returnPressed.connect(self.send_message)
        
        # 添加一些示例数据
        self.add_sample_data()
        
    def add_sample_data(self):
        # 添加示例成员
        members = ["少年阿磊", "云舒", "名字过长10604", "可乐", "z龙"]
        for member in members:
            item = QtWidgets.QListWidgetItem()
            widget = self.create_member_widget(member)
            item.setSizeHint(widget.sizeHint())
            self.memberList.addItem(item)
            self.memberList.setItemWidget(item, widget)
            
        # 添加示例消息
        messages = [
            ("统一牛奶", "牛哥"),
            ("统一牛奶", "能换大米吗"),
            ("高级牛奶", "兄弟们点点赞，给大家看照片")
        ]
        for author, text in messages:
            item = QtWidgets.QListWidgetItem()
            widget = self.create_message_widget(author, text)
            item.setSizeHint(widget.sizeHint())
            self.messageArea.addItem(item)
            self.messageArea.setItemWidget(item, widget)
    
    def create_member_widget(self, username):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        
        # 头像
        avatar = QtWidgets.QLabel()
        pixmap = QPixmap("path_to_avatar.png").scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio)
        avatar.setPixmap(pixmap)
        avatar.setFixedSize(32, 32)
        
        # 用户名
        name = QtWidgets.QLabel(username)
        name.setStyleSheet("color: #FFFFFF;")
        
        layout.addWidget(avatar)
        layout.addWidget(name)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_message_widget(self, author, text):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        
        # 头像
        avatar = QtWidgets.QLabel()
        pixmap = QPixmap("path_to_avatar.png").scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio)
        avatar.setPixmap(pixmap)
        avatar.setFixedSize(40, 40)
        
        # 消息内容
        msg_layout = QtWidgets.QVBoxLayout()
        author_label = QtWidgets.QLabel(author)
        author_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        text_label = QtWidgets.QLabel(text)
        text_label.setStyleSheet("color: #FFFFFF;")
        msg_layout.addWidget(author_label)
        msg_layout.addWidget(text_label)
        
        layout.addWidget(avatar)
        layout.addLayout(msg_layout)
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def send_message(self):
        text = self.messageInput.text().strip()
        if text:
            item = QtWidgets.QListWidgetItem()
            widget = self.create_message_widget("我", text)
            item.setSizeHint(widget.sizeHint())
            self.messageArea.addItem(item)
            self.messageArea.setItemWidget(item, widget)
            self.messageInput.clear()
            self.messageArea.scrollToBottom()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())