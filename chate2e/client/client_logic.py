import sys
import uuid
from PyQt6.QtWidgets import (
    QApplication, QListWidgetItem, QMessageBox, QDialog,
    QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QFileDialog
)
from PyQt6.QtCore import Qt

from chate2e.client.models import Message, DataManager
from chate2e.crypto.protocol.x3dh import X3DHProtocol
from chate2e.client.chat_ui import ChatWindowUI, ContactItem, ChatItem, DEFAULT_AVATAR_PATH
from chate2e.client.network_service import ClientNetworkService


class ChatWindow(ChatWindowUI):
    def __init__(self, current_user_id):
        super().__init__()
        self.current_session_id = None
        self.current_user_id = current_user_id
        
        self.network_service = ClientNetworkService()

        # 初始化数据管理器
        self.data_manager = DataManager()

        # 初始化 X3DH 协议实例
        self.x3dh = X3DHProtocol(current_user_id)

        # 加载联系人列表
        self.load_contacts()

        # 用户信息
        current_user = self.data_manager.users.get(self.current_user_id)
        if current_user:
            self.user_info = ContactItem(
                current_user.avatar_path,
                current_user.username,
                status="online"
            )
            self.left_layout.insertWidget(0, self.user_info)

        # 绑定事件
        self.send_btn.clicked.connect(self.handle_send_message)
        self.message_input.returnPressed.connect(self.handle_send_message)
        self.upload_btn.clicked.connect(self.handle_file_upload)
        self.contact_list.itemClicked.connect(self.on_contact_selected)
        self.add_contact_btn.clicked.connect(self.show_add_contact_dialog)

    def load_contacts(self):
        """加载联系人列表"""
        self.contact_list.clear()
        current_user = self.data_manager.users.get(self.current_user_id)
        if not current_user:
            return

        for contact_id in current_user.contacts:
            contact = self.data_manager.users.get(contact_id)
            if contact:
                # 获取最近的会话
                sessions = self.data_manager.get_user_sessions(self.current_user_id)
                last_message = ""
                for session in sessions:
                    if contact_id in [session.participant1_id, session.participant2_id]:
                        if session.last_message:
                            last_message = session.last_message.get('content', '')[:30]
                            break

                item = QListWidgetItem()
                widget = ContactItem(
                    contact.avatar_path,
                    contact.username,
                    last_message,
                    contact.status
                )
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.ItemDataRole.UserRole, contact.user_id)
                self.contact_list.addItem(item)
                self.contact_list.setItemWidget(item, widget)

    def load_messages(self, session_id: str):
        """加载会话消息"""
        self.messages_area.clear()
        messages = self.data_manager.load_messages(session_id)

        for message in messages:
            item = QListWidgetItem(self.messages_area)
            is_sender = message.sender_id == self.current_user_id
            sender = self.data_manager.users.get(message.sender_id)

            # 解密消息（如果需要）
            display_content = message.content
            if message.encryption:
                try:
                    receiver_id = message.receiver_id
                    shared_secret = self.x3dh.get_shared_secret_passive(
                        receiver_id if is_sender else message.sender_id
                    )
                    if shared_secret:
                        # 解密消息
                        iv = bytes.fromhex(message.encryption['iv'])
                        ciphertext = bytes.fromhex(message.encryption['ciphertext'])
                        tag = bytes.fromhex(message.encryption['tag'])
                        encrypted = ciphertext + tag
                        decrypted = self.x3dh.crypto_helper.decrypt_aes_gcm(
                            shared_secret,
                            encrypted,
                            iv
                        )
                        display_content = decrypted.decode()
                    else:
                        display_content = "无法获取解密密钥"
                except Exception as e:
                    display_content = f"消息解密失败: {str(e)}"

            widget = ChatItem(
                sender.avatar_path if sender else DEFAULT_AVATAR_PATH,
                sender.username if sender else "未知用户",
                display_content,
                is_sender
            )
            item.setSizeHint(widget.sizeHint())
            self.messages_area.setItemWidget(item, widget)

        # 滚动到最新消息
        self.messages_area.scrollToBottom()

    def on_contact_selected(self, item: QListWidgetItem):
        """处理联系人选择事件"""
        contact_id = item.data(Qt.ItemDataRole.UserRole)
        contact = self.data_manager.users.get(contact_id)
        if not contact:
            return

        # 更新聊天标题
        self.chat_header.setText(f"与 {contact.username} 的对话")

        # 获取或创建会话
        session = self.data_manager.get_or_create_session(
            self.current_user_id,
            contact_id
        )
        self.current_session_id = session.session_id

        # 加载消息
        self.load_messages(session.session_id)

    def handle_send_message(self):
        """处理发送消息"""
        if not self.current_session_id:
            return

        content = self.message_input.text().strip()
        if not content:
            return

        session = self.data_manager.sessions.get(self.current_session_id)
        if not session:
            return

        # 确定接收者ID
        receiver_id = session.participant2_id
        if receiver_id == self.current_user_id:
            receiver_id = session.participant1_id

        # 获取共享密钥
        shared_secret = self.x3dh.get_shared_secret_active(receiver_id)
        if not shared_secret:
            QMessageBox.warning(self, "错误", f"无法获取与 {receiver_id} 的共享密钥")
            return

        try:
            # 加密消息
            iv = self.x3dh.crypto_helper.get_random_bytes(12)
            encrypted = self.x3dh.crypto_helper.encrypt_aes_gcm(
                shared_secret,
                content.encode(),
                iv
            )
            ciphertext = encrypted[:-16]
            tag = encrypted[-16:]

            # 创建消息对象
            message = Message(
                message_id=str(uuid.uuid4()),
                session_id=self.current_session_id,
                sender_id=self.current_user_id,
                receiver_id=receiver_id,
                content=content,
                encryption={
                    "iv": iv.hex(),
                    "ciphertext": ciphertext.hex(),
                    "tag": tag.hex()
                }
            )

            # 保存消息
            self.data_manager.save_message(message)

            # 清空输入框
            self.message_input.clear()

            # 重新加载消息
            self.load_messages(self.current_session_id)

        except Exception as e:
            QMessageBox.warning(self, "错误", f"消息发送失败: {str(e)}")

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
        user_bundle = self.network_service.get_key_bundle(user_id)
        if not user_bundle:
            QMessageBox.warning(self, "警告", "用户不存在")
            return

        # 检查是否已经是联系人
        current_user = self.data_manager.users[self.current_user_id]
        if user_id in current_user.contacts:
            QMessageBox.warning(self, "警告", "联系人已存在")
            return

        # 更新联系人列表
        current_user.contacts.append(user_id)
        self.data_manager.save_data()

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
    window1.show()
    window2.show()

    sys.exit(app.exec())