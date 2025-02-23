import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QListWidgetItem, QMessageBox, QDialog,
    QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QFileDialog
)

from chate2e.client.chat_ui import ChatWindowUI, ContactItem, ChatItem, DEFAULT_AVATAR_PATH
from chate2e.client.client_server import ChatClient
from chate2e.client.models import Message, DataManager, Friend, UserStatus
from chate2e.model.message import MessageType


class ChatWindow(ChatWindowUI):
    def __init__(self, current_user_id: str,chat_client: ChatClient ,data_manager: DataManager):
        super().__init__()

        self.chat_client = chat_client
        self.current_session_id = None
        self.current_user_id = current_user_id

        # 初始化数据管理器
        self.data_manager = data_manager

        #注册消息处理器
        self.chat_client.register_message_handler(self.handle_received_message)

        # 加载联系人列表
        self.load_contacts()

        # 用户信息
        current_user = self.data_manager.user
        if current_user:
            self.user_info = ContactItem(
                current_user.avatar_path,
                current_user.username,
                status="online"
            )
            self.left_layout.insertWidget(0, self.user_info)

        # self.selected_contact: Friend
        self.selected_contact = None

        # 绑定事件
        self.send_btn.clicked.connect(self.handle_send_message)
        self.message_input.returnPressed.connect(self.handle_send_message)
        self.upload_btn.clicked.connect(self.handle_file_upload)
        self.contact_list.itemClicked.connect(self.on_contact_selected)
        self.add_contact_btn.clicked.connect(self.show_add_contact_dialog)

    def load_contacts(self):
        """加载联系人列表"""
        self.contact_list.clear()
        current_user = self.data_manager.user
        if not current_user:
            return

        for friend in current_user.friends:
           
            # 更新会话的最后一条消息
            last_message = self.data_manager.get_last_message(friend.user_id)
            item = QListWidgetItem()
            widget = ContactItem(
                friend.avatar_path,
                friend.username,
                last_message.encrypted_content if last_message else "",
                friend.status
            )
            item.setSizeHint(widget.sizeHint())
            # 存储 user_id 而不是整个 Friend 对象
            item.setData(Qt.ItemDataRole.UserRole, friend.user_id)
            self.contact_list.addItem(item)
            self.contact_list.setItemWidget(item, widget)

    def load_messages(self, session_id: str):
        """加载会话消息"""
        self.messages_area.clear()
        session = self.data_manager.sessions.get(session_id)
        if not session:
            return
        messages = session.messages
        if not messages or len(messages) == 0:
            return

        for message in messages:
            #如果消息的类型是init,则不显示
            if message.header.message_type == MessageType.INITIATE:
                continue
            item = QListWidgetItem(self.messages_area)
            is_sender = message.header.sender_id == self.current_user_id
            
            # 获取发送者信息
            sender = None
            if message.header.sender_id == self.data_manager.user.user_id:
                sender = self.data_manager.user
            else:
                friend = self.data_manager.user.get_friend(message.header.sender_id)
                sender = friend if friend else None

            # 如果发送者信息获取失败，使用默认值
            avatar_path = DEFAULT_AVATAR_PATH
            username = "未知用户"
            if sender:
                avatar_path = sender.avatar_path
                username = sender.username

            # 确保消息内容是字符串
            display_content = message.encrypted_content
            if isinstance(display_content, bytes):
                try:
                    display_content = display_content.decode('utf-8')

                except UnicodeDecodeError:
                    display_content = str(display_content)

            widget = ChatItem(
                avatar_path,
                username,
                display_content,
                is_sender
            )
            item.setSizeHint(widget.sizeHint())
            self.messages_area.setItemWidget(item, widget)

        # 滚动到最新消息
        self.messages_area.scrollToBottom()

    def on_contact_selected(self, item: QListWidgetItem):
        """处理联系人选择事件"""
        friend_id = item.data(Qt.ItemDataRole.UserRole)
        if not friend_id:
            return

        # 从当前用户的联系人列表中获取联系人信息
        current_user = self.data_manager.user
        friend_contact = current_user.get_friend(friend_id)
        if not friend_contact:
            return

        # 更新聊天标题
        self.chat_header.setText(f"与 {friend_contact.username} 的对话")

        # 获取或创建会话
        session = self.data_manager.get_or_create_session(
            friend_contact.user_id
        )
        self.current_session_id = session.session_id
        self.selected_contact = friend_contact

        # 加载消息
        self.load_messages(session.session_id)

        # 清空输入框并设置焦点
        self.message_input.clear()
        self.message_input.setFocus()


    def handle_send_message(self):
        """处理发送消息"""
        if not self.current_session_id or not self.selected_contact:
            return

        content = self.message_input.text().strip()
        if not content:
            return

        session = self.data_manager.sessions.get(self.current_session_id)
        if not session:
            return

        if not self.chat_client.protocol.session_initialized:
            if not self.chat_client.init_session_sync(self.selected_contact.user_id,self.current_session_id):
                QMessageBox.warning(self, "错误", "会话初始化失败")
                return

        try:
            # 加密消息
            encrypted_message = self.chat_client.protocol.encrypt_message(content)
            #从加密消息中重组消息

            decrypted_message =  Message(
                message_id=encrypted_message.header.message_id,
                sender_id=encrypted_message.header.sender_id,
                session_id=encrypted_message.header.session_id,
                receiver_id=encrypted_message.header.receiver_id,
                encryption=encrypted_message.encryption,
                message_type=MessageType.MESSAGE,
                encrypted_content= content.encode('utf-8')
            )

            # 发送消息到服务器
            if self.chat_client.send_message_sync(self.selected_contact.user_id, encrypted_message):

                self.data_manager.add_message(session.session_id, decrypted_message)

                # 清空输入框
                self.message_input.clear()

                # 重新加载消息
                self.load_messages(self.current_session_id)
            else:
                QMessageBox.warning(self, "错误", "消息发送失败")

        except Exception as e:
            QMessageBox.warning(self, "错误", f"消息发送失败: {str(e)}")


    def handle_received_message(self, message: Message):
        """处理接收到的消息"""
        try:
            # 解密消息
            decrypted_text = self.chat_client.protocol.decrypt_message(message)
            # 获取或创建会话
            session = self.data_manager.get_or_create_session(message.header.sender_id)


            # 创建新的消息对象（包含解密后的内容）
            message_obj = Message(
                message_id=message.header.message_id,
                session_id=session.session_id,
                sender_id=message.header.sender_id,
                receiver_id=message.header.receiver_id,
                encrypted_content=decrypted_text,  # 存储解密后的内容
                message_type=MessageType.MESSAGE,
                encryption=message.encryption  # 保留加密信息
            )

            # 保存消息
            self.data_manager.add_message(session.session_id, message_obj)

            # 如果是当前会话，刷新消息列表
            if session.session_id == self.current_session_id:
                self.load_messages(session.session_id)
        except Exception as e:
            print(f"处理消息失败: {str(e)}")

    def handle_file_upload(self):
        """处理文件上传"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文件",
            "",
            "所有文件 (*.*)"
        )

        if file_path:
            # TODO: 实现文件上传逻辑
            print(f"选择的文件: {file_path}")

    def show_add_contact_dialog(self):
        """显示添加联系人对话框"""
        dialog = AddContactDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            user_id = dialog.user_id_input.text().strip()
            if user_id:
                self.add_contact(user_id)

    def add_contact(self, user_id: str):
        """
        添加联系人,联系人列表只存在于本地,每次启动时会重新加载本地文件,添加联系人需要到服务端获取联系人信息
        """
        if user_id == self.current_user_id:
            QMessageBox.warning(self, "警告", "不能添加自己为联系人")
            return

        # 检查用户是否存在 需要到服务端获取用户信息
        # user_bundle = self.chat_client.get_user_bundle(user_id)
        user_name = self.chat_client.get_user_name(user_id)
        if not user_name:
            QMessageBox.warning(self, "警告", "用户不存在")
            return
        
        # 假设用户存在，创建一个Friend对象
        new_friend = Friend(
            user_id=user_id,
            username=user_name,
            avatar_path=DEFAULT_AVATAR_PATH,  # 使用默认头像
            status= UserStatus.ONLINE
        )

        # 检查是否已经是联系人
        current_user = self.data_manager.user
        if current_user.get_friend(user_id):
            QMessageBox.warning(self, "警告", "联系人已存在")
            return

        # 更新联系人列表
        self.data_manager.add_friend(new_friend)
        
        # 刷新联系人列表
        self.load_contacts()
        QMessageBox.information(self, "成功", "联系人添加成功")


class AddContactDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加联系人")
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QPushButton {
                padding: 8px 16px;
            }
        """)

        layout = QVBoxLayout()

        # 表单布局
        form_layout = QFormLayout()
        self.user_id_input = QLineEdit()
        form_layout.addRow("用户ID:", self.user_id_input)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 创建两个客户端窗口
    window1 = ChatWindow("u001")
    window2 = ChatWindow("u002")
    window1.setWindowTitle("Alice's Chat Window")
    window2.setWindowTitle("Bob's Chat Window")
    window1.show()
    window2.show()

    sys.exit(app.exec())