# -*- coding: utf-8 -*-
"""
本地化支持启动脚本
自动集成本地化语音处理到现有的enhanced_UI中
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入现有的UI模块
try:
    from enhanced_UI import EnhancedMainWindow
    UI_AVAILABLE = True
except ImportError:
    print("❌ enhanced_UI 不可用")
    UI_AVAILABLE = False

# 导入本地化适配器
try:
    from local_ui_adapter import apply_local_patches
    ADAPTER_AVAILABLE = True
except ImportError:
    print("❌ 本地化适配器不可用")
    ADAPTER_AVAILABLE = False

# 导入PyQt5
try:
    from PyQt5.QtWidgets import QApplication, QMessageBox
    from PyQt5.QtCore import Qt
    PYQT_AVAILABLE = True
except ImportError:
    print("❌ PyQt5 不可用")
    PYQT_AVAILABLE = False

def check_dependencies():
    """检查所有依赖"""
    missing_deps = []
    
    if not UI_AVAILABLE:
        missing_deps.append("enhanced_UI")
    
    if not ADAPTER_AVAILABLE:
        missing_deps.append("local_ui_adapter")
    
    if not PYQT_AVAILABLE:
        missing_deps.append("PyQt5")
    
    return missing_deps

def show_welcome_message():
    """显示欢迎消息"""
    print("=" * 60)
    print("🎯 语音替换系统 - 本地化增强版")
    print("=" * 60)
    print("✨ 新功能：完全离线的语音处理")
    print("🔧 集成了以下本地化模型：")
    print("   • Whisper - 高质量语音识别")
    print("   • pyttsx3 - 本地语音合成")
    print("   • Argos Translate - 离线翻译")
    print("=" * 60)

def show_dependency_help():
    """显示依赖安装帮助"""
    help_text = """
🔧 缺少依赖，请按以下步骤安装：

1️⃣ 安装基础依赖：
   pip install PyQt5

2️⃣ 安装本地化模型：
   python install_local_dependencies.py

3️⃣ 重新运行程序：
   python launch_with_local_support.py

💡 提示：
- 首次安装可能需要下载较大的模型文件
- 请确保网络连接稳定
- 安装完成后即可完全离线使用
"""
    print(help_text)

def create_enhanced_main_window():
    """创建增强的主窗口"""
    try:
        # 创建主窗口
        main_window = EnhancedMainWindow()
        
        # 应用本地化补丁
        if ADAPTER_AVAILABLE:
            apply_local_patches(main_window)
            print("✅ 本地化功能已集成")
        else:
            print("⚠️ 本地化功能不可用，使用原始API模式")
        
        return main_window
        
    except Exception as e:
        print(f"❌ 创建主窗口失败: {e}")
        return None

def main():
    """主函数"""
    # 显示欢迎消息
    show_welcome_message()
    
    # 检查依赖
    missing_deps = check_dependencies()
    if missing_deps:
        print(f"❌ 缺少依赖: {', '.join(missing_deps)}")
        show_dependency_help()
        return
    
    try:
        # 创建应用
        app = QApplication(sys.argv)
        app.setApplicationName("语音替换系统 - 本地化增强版")
        app.setOrganizationName("LocalSpeechProcessor")
        
        # 设置应用样式
        app.setStyle("Fusion")
        
        # 创建主窗口
        main_window = create_enhanced_main_window()
        if not main_window:
            QMessageBox.critical(None, "错误", "无法创建主窗口")
            return
        
        # 显示窗口
        main_window.show()
        
        # 显示启动成功消息
        print("🚀 应用启动成功")
        print("💡 点击'开始处理'时将可以选择使用本地化处理")
        
        # 运行应用
        sys.exit(app.exec_())
        
    except Exception as e:
        error_msg = f"应用启动失败: {str(e)}"
        print(f"❌ {error_msg}")
        
        if PYQT_AVAILABLE:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "启动错误", error_msg)

if __name__ == "__main__":
    main() 