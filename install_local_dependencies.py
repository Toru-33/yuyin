# -*- coding: utf-8 -*-
"""
本地化依赖安装脚本
自动安装 Whisper、pyttsx3、Argos Translate 等本地AI模型
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True, encoding='utf-8')
        print(f"✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败: {e}")
        if e.stdout:
            print(f"输出: {e.stdout}")
        if e.stderr:
            print(f"错误: {e.stderr}")
        return False

def install_dependencies():
    """安装所有本地化依赖"""
    print("🚀 开始安装本地化语音处理依赖...")
    
    # 基础依赖
    basic_packages = [
        "openai-whisper",      # 语音识别
        "pyttsx3",             # 语音合成
        "argostranslate",      # 翻译
        "pydub",               # 音频处理
        "moviepy",             # 视频处理
        "torch",               # PyTorch (Whisper依赖)
        "torchaudio",          # 音频处理
        "transformers",        # 备用翻译模型
    ]
    
    print("📦 安装基础包...")
    for package in basic_packages:
        success = run_command(f"pip install {package}", f"安装 {package}")
        if not success:
            print(f"⚠️ {package} 安装失败，继续安装其他包...")
    
    # 额外的音频处理工具
    print("\n🔧 安装额外音频工具...")
    audio_tools = [
        "ffmpeg-python",       # FFmpeg Python绑定
        "librosa",             # 音频分析
        "soundfile",           # 音频文件处理
    ]
    
    for tool in audio_tools:
        run_command(f"pip install {tool}", f"安装 {tool}")
    
    # 检查FFmpeg是否可用
    print("\n🎵 检查FFmpeg...")
    if run_command("ffmpeg -version", "检查FFmpeg"):
        print("✅ FFmpeg 可用")
    else:
        print("⚠️ FFmpeg 不可用，请手动安装")
        print("   Windows: 从 https://ffmpeg.org/download.html 下载")
        print("   或使用: winget install ffmpeg")
    
    print("\n🎉 依赖安装完成！")

def test_installations():
    """测试安装是否成功"""
    print("\n🧪 测试安装...")
    
    # 测试 Whisper
    try:
        import whisper
        print("✅ Whisper 可用")
    except ImportError:
        print("❌ Whisper 不可用")
    
    # 测试 pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        print("✅ pyttsx3 可用")
    except ImportError:
        print("❌ pyttsx3 不可用")
    except Exception as e:
        print(f"❌ pyttsx3 初始化失败: {e}")
    
    # 测试 Argos Translate
    try:
        import argostranslate.package
        import argostranslate.translate
        print("✅ Argos Translate 可用")
    except ImportError:
        print("❌ Argos Translate 不可用")
    
    # 测试 PyDub
    try:
        from pydub import AudioSegment
        print("✅ PyDub 可用")
    except ImportError:
        print("❌ PyDub 不可用")
    
    # 测试 MoviePy
    try:
        from moviepy.editor import VideoFileClip
        print("✅ MoviePy 可用")
    except ImportError:
        print("❌ MoviePy 不可用")

def create_requirements_file():
    """创建requirements文件"""
    requirements = """# 本地化语音处理依赖
openai-whisper>=20231117
pyttsx3>=2.90
argostranslate>=1.9.0
pydub>=0.25.1
moviepy>=1.0.3
torch>=2.0.0
torchaudio>=2.0.0
transformers>=4.30.0
ffmpeg-python>=0.2.0
librosa>=0.10.0
soundfile>=0.12.0
numpy>=1.21.0
requests>=2.25.0
"""
    
    with open("requirements_local.txt", "w", encoding="utf-8") as f:
        f.write(requirements)
    
    print("✅ 创建 requirements_local.txt 文件")

def main():
    """主函数"""
    print("🎯 本地化语音处理系统安装器")
    print("=" * 50)
    
    # 创建requirements文件
    create_requirements_file()
    
    # 安装依赖
    install_dependencies()
    
    # 测试安装
    test_installations()
    
    print("\n" + "=" * 50)
    print("🎉 安装完成！")
    print("\n📋 下一步:")
    print("1. 运行 python local_speech_processor.py 测试系统")
    print("2. 在你的项目中导入并使用 LocalSpeechProcessor")
    print("3. 如有问题，请检查上述测试结果")

if __name__ == "__main__":
    main() 