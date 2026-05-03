"""
AI协同小说编辑器 - 主入口
纯本地 · AES-256加密 · AI深度协同 · 隐私安全

启动命令: python main.py
"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.app import Application


def main():
    """主函数"""
    print("=" * 60)
    print("  AI协同小说编辑器 v1.0.0")
    print("  纯本地存储 | AES-256加密 | Agent深度协同")
    print("=" * 60)

    # 检查Python版本
    Application.check_python_version()

    # 检查依赖
    Application.check_dependencies()

    # 启动应用
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
