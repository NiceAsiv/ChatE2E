import sys

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QListWidgetItem, QMessageBox, QDialog,
    QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QFileDialog, QMenu
)

from chate2e.client.chat_ui import ChatWindowUI, ContactItem, ChatItem, DEFAULT_AVATAR_PATH
from chate2e.client.client_server import ChatClient
from chate2e.client.models import Message, DataManager, Friend, UserStatus
from chate2e.model.message import MessageType


class ChatWindow(ChatWindowUI):
    # 定义信号
    friend_list_update_signal = pyqtSignal()
    message_received_signal = pyqtSignal(str)

    def __init__(self, current_user_id: str,chat_client: ChatClient ,data_manager: DataManager):
        super().__init__()

        self.chat_client = chat_client
        self.current_session_id = None
        self.current_user_id = current_user_id

        # 初始化数据管理器
        self.data_manager = data_manager

        #注册消息处理器
        self.chat_client.register_message_handler(self.handle_received_message)
        
        # 连接信号到槽
        self.friend_list_update_signal.connect(self.load_contacts)
        self.message_received_signal.connect(self.on_message_received)
        
        # 注册好友更新处理器
        self.chat_client.register_friend_update_handler(self.on_friend_list_updated)

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
        
        # 设置联系人列表右键菜单
        self.contact_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.contact_list.customContextMenuRequested.connect(self.show_contact_context_menu)

    def load_contacts(self):
        """加载联系人列表"""
        self.contact_list.clear()
        current_user = self.data_manager.user
        if not current_user:
            return

        for friend in current_user.friends:
           
            # 更新会话的最后一条消息
            last_message = self.data_manager.get_last_message(friend.user_id)
            
            display_content = ""
            if last_message:
                display_content = last_message.encrypted_content
                if isinstance(display_content, bytes):
                    try:
                        display_content = display_content.decode('utf-8')
                    except UnicodeDecodeError:
                        display_content = str(display_content)

            item = QListWidgetItem()
            widget = ContactItem(
                friend.avatar_path,
                friend.username,
                display_content,
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

        # 从服务器获取或创建会话
        try:
            import requests
            response = requests.post(
                f"{self.chat_client.server_url}/session/get",
                json={
                    'user1_id': self.current_user_id,
                    'user2_id': friend_contact.user_id
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                server_session_id = result['session_id']
                print(f"[UI] 从服务器获取会话ID: {server_session_id}")
                
                # 使用服务器返回的session_id获取或创建本地会话
                session = self.data_manager.get_or_create_session_with_id(
                    server_session_id,
                    friend_contact.user_id
                )
            else:
                print(f"[UI] 从服务器获取会话ID失败，使用本地创建")
                session = self.data_manager.get_or_create_session(friend_contact.user_id)
                
        except Exception as e:
            print(f"[UI] 获取服务器会话ID异常: {e}，使用本地创建")
            session = self.data_manager.get_or_create_session(friend_contact.user_id)
        
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

        # 检查与当前联系人的会话是否已初始化
        peer_id = self.selected_contact.user_id
        if not self.chat_client.sessions.get(peer_id):
            # 初始化会话，传入当前的session_id
            success, returned_session_id = self.chat_client.init_session_sync(peer_id, self.current_session_id)
            if not success:
                QMessageBox.warning(self, "错误", "会话初始化失败")
                return
            
            # 确保session_id一致
            if returned_session_id != self.current_session_id:
                print(f"[UI] 警告: 服务器返回的session_id与本地不同，更新本地session_id")
                self.current_session_id = returned_session_id

        try:
            # 确保协议层使用正确的session_id
            self.chat_client.protocol.session_id = self.current_session_id
            self.chat_client.protocol.peer_id = peer_id
            
            # 加密消息
            encrypted_message = self.chat_client.protocol.encrypt_message(content)
            print(f"[UI] 当前会话ID: {self.current_session_id}")
            print(f"[UI] 加密消息中的session_id: {encrypted_message.header.session_id}")
            
            #从加密消息中重组消息，使用当前会话的session_id
            decrypted_message =  Message(
                message_id=encrypted_message.header.message_id,
                sender_id=encrypted_message.header.sender_id,
                session_id=self.current_session_id,  # 使用当前会话ID
                receiver_id=encrypted_message.header.receiver_id,
                encryption=encrypted_message.encryption,
                message_type=MessageType.MESSAGE,
                encrypted_content= content.encode('utf-8')
            )

            # 发送消息到服务器
            if self.chat_client.send_message_sync(self.selected_contact.user_id, encrypted_message):
                print(f"[UI] 保存消息到会话: {self.current_session_id}")
                self.data_manager.add_message(self.current_session_id, decrypted_message)

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
            # 获取或创建会话 - 使用消息中的session_id
            session = self.data_manager.get_or_create_session_with_id(
                message.header.session_id,
                message.header.sender_id
            )

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

            # 发送信号更新UI
            self.message_received_signal.emit(session.session_id)
            
        except Exception as e:
            print(f"处理消息失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_message_received(self, session_id: str):
        """在主线程中更新UI"""
        # 如果是当前会话，刷新消息列表
        if session_id == self.current_session_id:
            self.load_messages(session_id)
        
        # 刷新联系人列表以更新最后一条消息
        self.load_contacts()

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
    
    def on_friend_list_updated(self):
        """当好友列表更新时调用（可能在非主线程）"""
        print("好友列表已更新，发送信号刷新UI")
        # 发射信号，在主线程中执行
        self.friend_list_update_signal.emit()
    
    def show_contact_context_menu(self, position):
        """显示联系人右键菜单"""
        item = self.contact_list.itemAt(position)
        if not item:
            return
        
        friend_id = item.data(Qt.ItemDataRole.UserRole)
        if not friend_id:
            return
        
        # 创建右键菜单
        menu = QMenu(self)
        delete_action = menu.addAction("删除好友")
        
        # 显示菜单并获取选中的操作
        action = menu.exec(self.contact_list.mapToGlobal(position))
        
        if action == delete_action:
            self.delete_friend(friend_id)
    
    def delete_friend(self, friend_id: str):
        """删除好友"""
        # 获取好友信息
        friend = self.data_manager.user.get_friend(friend_id)
        if not friend:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除好友 {friend.username} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 从本地删除
            if self.data_manager.user.remove_friend(friend_id):
                self.data_manager.save_user_profile()
                
                # 通知服务器
                if self.chat_client.remove_friend_sync(friend_id):
                    print(f"已删除好友: {friend.username}")
                
                # 刷新联系人列表
                self.load_contacts()
                
                # 如果当前正在和这个好友聊天，清空聊天区域
                if self.selected_contact and self.selected_contact.user_id == friend_id:
                    self.selected_contact = None
                    self.current_session_id = None
                    self.messages_area.clear()
                    self.chat_header.setText("请选择联系人")
                
                QMessageBox.information(self, "成功", "好友已删除")
            else:
                QMessageBox.warning(self, "错误", "删除好友失败")

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
        
        # 通知服务器，让对方也添加自己为好友
        if self.chat_client.add_friend_sync(user_id):
            print(f"已发送好友请求给 {user_name}")
        
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