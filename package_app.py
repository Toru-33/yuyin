# -*- coding: utf-8 -*-
"""
语音替换工具打包脚本 v2.0
集成FFmpeg，无需用户配置环境
"""

import os
import sys
import subprocess
import shutil
import zipfile
import requests
from pathlib import Path

class AppPackager:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.build_dir = self.project_dir / "build"
        self.dist_dir = self.project_dir / "dist" 
        self.ffmpeg_dir = self.project_dir / "ffmpeg"
        
    def download_ffmpeg(self):
        """下载并解压FFmpeg"""
        print("📥 正在下载FFmpeg...")
        
        # FFmpeg Windows版本下载链接
        ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        
        # 创建ffmpeg目录
        self.ffmpeg_dir.mkdir(exist_ok=True)
        
        # 检查是否已存在
        ffmpeg_exe = self.ffmpeg_dir / "bin" / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            print("✅ FFmpeg已存在，跳过下载")
            return True
            
        try:
            # 下载FFmpeg
            zip_path = self.ffmpeg_dir / "ffmpeg.zip"
            print(f"   下载到: {zip_path}")
            
            with requests.get(ffmpeg_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                print(f"\r   下载进度: {progress:.1f}%", end="", flush=True)
            
            print("\n📦 正在解压FFmpeg...")
            
            # 解压到临时目录
            temp_dir = self.ffmpeg_dir / "temp"
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 查找解压后的FFmpeg目录
            for item in temp_dir.iterdir():
                if item.is_dir() and "ffmpeg" in item.name.lower():
                    # 移动bin目录到我们的ffmpeg目录
                    src_bin = item / "bin"
                    if src_bin.exists():
                        dst_bin = self.ffmpeg_dir / "bin"
                        if dst_bin.exists():
                            shutil.rmtree(dst_bin)
                        shutil.copytree(src_bin, dst_bin)
                        print("✅ FFmpeg解压完成")
                        break
            
            # 清理临时文件
            shutil.rmtree(temp_dir)
            zip_path.unlink()
            
            # 验证FFmpeg
            if ffmpeg_exe.exists():
                print("✅ FFmpeg安装成功")
                return True
            else:
                print("❌ FFmpeg安装失败")
                return False
                
        except Exception as e:
            print(f"❌ 下载FFmpeg失败: {e}")
            return False
    
    def create_requirements(self):
        """创建requirements.txt"""
        requirements = [
            "PyQt5>=5.15.0",
            "moviepy>=1.0.3", 
            "requests>=2.25.0",
            "websocket-client>=1.0.0",
            "pydub>=0.25.0",
            "Pillow>=8.0.0",
            "numpy>=1.19.0"
        ]
        
        req_file = self.project_dir / "requirements.txt"
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(requirements))
        
        print("✅ requirements.txt已创建")
    
    def create_spec_file(self):
        """创建PyInstaller spec文件"""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
project_dir = Path(r"{self.project_dir}")

# 收集所有必要文件
datas = [
    (str(project_dir / "style.qss"), "."),
    (str(project_dir / "style_dark.qss"), "."),
    (str(project_dir / "*.py"), "."),
    (str(project_dir / "ffmpeg"), "ffmpeg"),
]

# 收集所有Python模块
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtWidgets', 
    'PyQt5.QtGui',
    'moviepy.editor',
    'requests',
    'websocket',
    'pydub',
    'PIL',
    'numpy'
]

a = Analysis(
    [str(project_dir / "enhanced_UI.py")],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='语音替换工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='语音替换工具',
)
'''
        
        spec_file = self.project_dir / "app.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print("✅ PyInstaller spec文件已创建")
        return spec_file
    
    def build_executable(self):
        """构建可执行文件"""
        print("🔨 正在构建可执行文件...")
        
        try:
            # 创建spec文件
            spec_file = self.create_spec_file()
            
            # 运行PyInstaller
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",
                "--noconfirm", 
                str(spec_file)
            ]
            
            print(f"   执行命令: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ 可执行文件构建成功")
                return True
            else:
                print(f"❌ 构建失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ 构建异常: {e}")
            return False
    
    def create_installer(self):
        """创建安装包"""
        print("📦 正在创建安装包...")
        
        dist_app_dir = self.dist_dir / "语音替换工具"
        if not dist_app_dir.exists():
            print("❌ 未找到构建输出目录")
            return False
        
        # 创建发布目录
        release_dir = self.project_dir / "final_release"
        release_dir.mkdir(exist_ok=True)
        
        # 复制到发布目录
        final_app_dir = release_dir / "语音替换工具"
        if final_app_dir.exists():
            shutil.rmtree(final_app_dir)
        
        shutil.copytree(dist_app_dir, final_app_dir)
        
        # 创建启动脚本
        start_script = final_app_dir / "启动工具.bat"
        with open(start_script, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('cd /d "%~dp0"\n')
            f.write('start "" "语音替换工具.exe"\n')
        
        # 创建README
        readme_file = final_app_dir / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write("语音替换工具 - 集成版\n")
            f.write("========================\n\n")
            f.write("这是一个完全独立的版本，无需安装任何额外软件！\n\n")
            f.write("使用方法：\n")
            f.write("1. 双击 '启动工具.bat' 或 '语音替换工具.exe'\n")
            f.write("2. 拖拽视频文件到界面\n")
            f.write("3. 选择输出目录\n")
            f.write("4. 选择转换类型\n")
            f.write("5. 点击开始转换\n\n")
            f.write("包含组件：\n")
            f.write("- 语音替换工具本体\n")
            f.write("- FFmpeg (视频处理)\n")
            f.write("- 所有必要的Python库\n\n")
            f.write("无需安装：\n")
            f.write("- Python\n")
            f.write("- FFmpeg\n")
            f.write("- 任何第三方库\n")
        
        print(f"✅ 安装包已创建: {final_app_dir}")
        return True
    
    def package(self):
        """完整打包流程"""
        print("🚀 开始打包语音替换工具...")
        
        # 步骤1: 下载FFmpeg
        if not self.download_ffmpeg():
            print("❌ FFmpeg下载失败，打包终止")
            return False
        
        # 步骤2: 创建requirements
        self.create_requirements()
        
        # 步骤3: 构建可执行文件
        if not self.build_executable():
            print("❌ 可执行文件构建失败，打包终止")
            return False
        
        # 步骤4: 创建安装包
        if not self.create_installer():
            print("❌ 安装包创建失败")
            return False
        
        print("🎉 打包完成！")
        print(f"输出目录: {self.project_dir / 'final_release'}")
        return True

def main():
    packager = AppPackager()
    
    print("语音替换工具打包器 v2.0")
    print("======================")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print("✅ PyInstaller已安装")
    except ImportError:
        print("❌ 请先安装PyInstaller: pip install pyinstaller")
        return False
    
    # 开始打包
    success = packager.package()
    
    if success:
        print("\n🎉 打包成功！")
        print("现在您可以将final_release文件夹分发给用户了")
    else:
        print("\n❌ 打包失败")
        
    return success

if __name__ == "__main__":
    main() 