import sys
from chate2e.ui.login_window import LoginWindow

def main():
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    login_window = LoginWindow()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()