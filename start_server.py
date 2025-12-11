#!/usr/bin/env python3
"""
ChatE2E 服务器启动脚本
"""
import os
import sys

# 确保项目根目录在 Python 路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from chate2e.server.app import app, socketio

if __name__ == '__main__':
    print("=== ChatE2E 服务器启动 ===")
    print("服务器地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务器")
    print("=" * 30)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    
    # 启动 SocketIO 服务器
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
