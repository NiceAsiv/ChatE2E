from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_ChatWindow(object):
    def setupUi(self, ChatWindow):
        ChatWindow.setObjectName("ChatWindow")
        ChatWindow.resize(1200, 800)
        ChatWindow.setMinimumSize(QtCore.QSize(1200, 800))
        ChatWindow.setStyleSheet("QMainWindow {\n"
"    background-color: #363636;\n"
"}")
        self.centralwidget = QtWidgets.QWidget(parent=ChatWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.leftSidebar = QtWidgets.QWidget(parent=self.centralwidget)
        self.leftSidebar.setMinimumSize(QtCore.QSize(200, 0))
        self.leftSidebar.setMaximumSize(QtCore.QSize(200, 16777215))
        self.leftSidebar.setStyleSheet("background-color: #2B2B2B;")
        self.leftSidebar.setObjectName("leftSidebar")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.leftSidebar)
        self.verticalLayout.setObjectName("verticalLayout")
        self.channelHeader = QtWidgets.QLabel(parent=self.leftSidebar)
        self.channelHeader.setStyleSheet("color: #FFFFFF;\n"
"font-size: 18px;\n"
"padding: 10px;")
        self.channelHeader.setObjectName("channelHeader")
        self.verticalLayout.addWidget(self.channelHeader)
        self.channelList = QtWidgets.QListWidget(parent=self.leftSidebar)
        self.channelList.setStyleSheet("QListWidget {\n"
"    background-color: #2B2B2B;\n"
"    border: none;\n"
"}\n"
"QListWidget::item {\n"
"    padding: 5px;\n"
"    color: #FFFFFF;\n"
"}\n"
"QListWidget::item:selected {\n"
"    background-color: #404040;\n"
"}")
        self.channelList.setObjectName("channelList")
        self.verticalLayout.addWidget(self.channelList)
        self.horizontalLayout.addWidget(self.leftSidebar)
        self.chatArea = QtWidgets.QWidget(parent=self.centralwidget)
        self.chatArea.setStyleSheet("background-color: #363636;")
        self.chatArea.setObjectName("chatArea")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.chatArea)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.chatHeader = QtWidgets.QLabel(parent=self.chatArea)
        self.chatHeader.setStyleSheet("color: #FFFFFF;\n"
"font-size: 16px;\n"
"padding: 10px;")
        self.chatHeader.setObjectName("chatHeader")
        self.verticalLayout_2.addWidget(self.chatHeader)
        self.messageArea = QtWidgets.QListWidget(parent=self.chatArea)
        self.messageArea.setStyleSheet("QListWidget {\n"
"    background-color: #363636;\n"
"    border: none;\n"
"}")
        self.messageArea.setObjectName("messageArea")
        self.verticalLayout_2.addWidget(self.messageArea)
        self.inputArea = QtWidgets.QWidget(parent=self.chatArea)
        self.inputArea.setObjectName("inputArea")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.inputArea)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.messageInput = QtWidgets.QLineEdit(parent=self.inputArea)
        self.messageInput.setMinimumSize(QtCore.QSize(0, 40))
        self.messageInput.setStyleSheet("QLineEdit {\n"
"    background-color: #2B2B2B;\n"
"    border: 1px solid #404040;\n"
"    border-radius: 4px;\n"
"    color: #FFFFFF;\n"
"    padding: 8px;\n"
"}")
        self.messageInput.setObjectName("messageInput")
        self.horizontalLayout_2.addWidget(self.messageInput)
        self.sendButton = QtWidgets.QPushButton(parent=self.inputArea)
        self.sendButton.setMinimumSize(QtCore.QSize(32, 32))
        self.sendButton.setMaximumSize(QtCore.QSize(32, 32))
        self.sendButton.setStyleSheet("QPushButton {\n"
"    background-color: #2B2B2B;\n"
"    border: 1px solid #404040;\n"
"    border-radius: 4px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #404040;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #505050;\n"
"}")
        self.sendButton.setObjectName("sendButton")
        self.horizontalLayout_2.addWidget(self.sendButton)
        self.verticalLayout_2.addWidget(self.inputArea)
        self.horizontalLayout.addWidget(self.chatArea)
        self.rightSidebar = QtWidgets.QWidget(parent=self.centralwidget)
        self.rightSidebar.setMinimumSize(QtCore.QSize(200, 0))
        self.rightSidebar.setMaximumSize(QtCore.QSize(200, 16777215))
        self.rightSidebar.setStyleSheet("background-color: #2B2B2B;")
        self.rightSidebar.setObjectName("rightSidebar")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.rightSidebar)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.memberHeader = QtWidgets.QLabel(parent=self.rightSidebar)
        self.memberHeader.setStyleSheet("color: #FFFFFF;\n"
"font-size: 14px;\n"
"padding: 10px;")
        self.memberHeader.setObjectName("memberHeader")
        self.verticalLayout_3.addWidget(self.memberHeader)
        self.memberList = QtWidgets.QListWidget(parent=self.rightSidebar)
        self.memberList.setStyleSheet("QListWidget {\n"
"    background-color: #2B2B2B;\n"
"    border: none;\n"
"}")
        self.memberList.setObjectName("memberList")
        self.verticalLayout_3.addWidget(self.memberList)
        self.horizontalLayout.addWidget(self.rightSidebar)
        ChatWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(ChatWindow)
        QtCore.QMetaObject.connectSlotsByName(ChatWindow)

    def retranslateUi(self, ChatWindow):
        _translate = QtCore.QCoreApplication.translate
        ChatWindow.setWindowTitle(_translate("ChatWindow", "聊天室"))
        self.channelHeader.setText(_translate("ChatWindow", "大哲聊"))
        self.chatHeader.setText(_translate("ChatWindow", "居然还有威望"))
        self.messageInput.setPlaceholderText(_translate("ChatWindow", "聊聊点什么吧~"))
        self.memberHeader.setText(_translate("ChatWindow", "群成员(7/53)"))
