#!/usr/bin/env python3
"""
ChatE2E 客户端启动脚本 - 第二个实例
用于测试多用户通信
"""
import os
import sys

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chate2e.client.main import ChatApp

if __name__ == "__main__":
    print("=== ChatE2E 客户端启动 (实例2) ===")
    app = ChatApp()
    sys.exit(app.run())
