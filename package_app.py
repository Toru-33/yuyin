# -*- coding: utf-8 -*-
"""
语音替换工具 - 完整打包程序
确保所有依赖都被正确包含，用户可直接运行
"""

import os
import sys
import subprocess
import shutil
import json
import datetime
from pathlib import Path

class PackageBuilder:
    def __init__(self):
        self.project_name = "YuYinTiHuan"
        self.main_script = "enhanced_UI.py"
        self.output_dir = "final_release"
        
    def print_banner(self):
        """打印横幅"""
        print("=" * 60)
        print("       语音替换工具 - 完整打包程序 v1.0")
        print("=" * 60)
        print()
        
    def check_environment(self):
        """检查打包环境"""
        print("🔍 检查打包环境...")
        
        # 检查主文件
        if not os.path.exists(self.main_script):
            print(f"❌ 找不到主文件: {self.main_script}")
            return False
            
        # 检查Python环境
        try:
            python_version = sys.version_info
            print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        except Exception as e:
            print(f"❌ Python环境检查失败: {e}")
            return False
            
        return True
    
    def install_dependencies(self):
        """安装并检查依赖"""
        print("📦 检查和安装依赖...")
        
        required_packages = [
            'pyinstaller',
            'PyQt5', 
            'websocket-client',
            'requests',
            'pydub',
            'moviepy',
            'numpy',
            'langdetect'
        ]
        
        for package in required_packages:
            try:
                print(f"   检查 {package}...", end="")
                if package == 'pyinstaller':
                    __import__('PyInstaller')
                elif package == 'websocket-client':
                    __import__('websocket')
                elif package == 'PyQt5':
                    __import__('PyQt5.QtCore')
                else:
                    __import__(package)
                print(" ✅")
            except ImportError:
                print(f" ❌ 缺失，正在安装...")
                try:
                    subprocess.check_call([
                        sys.executable, '-m', 'pip', 'install', package
                    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print(f"   {package} 安装成功 ✅")
                except subprocess.CalledProcessError as e:
                    print(f"   {package} 安装失败 ❌: {e}")
                    return False
        
        print("✅ 所有依赖检查完成")
        return True
    
    def clean_build_dirs(self):
        """清理构建目录"""
        print("🧹 清理旧的构建文件...")
        
        dirs_to_clean = ['build', 'dist', self.output_dir]
        for dir_name in dirs_to_clean:
            if os.path.exists(dir_name):
                try:
                    shutil.rmtree(dir_name)
                    print(f"   删除目录: {dir_name} ✅")
                except Exception as e:
                    print(f"   删除目录失败 {dir_name}: {e}")
        
        # 删除spec文件
        for spec_file in Path('.').glob('*.spec'):
            try:
                spec_file.unlink()
                print(f"   删除规格文件: {spec_file} ✅")
            except Exception as e:
                print(f"   删除规格文件失败: {e}")
    
    def create_spec_file(self):
        """创建PyInstaller规格文件"""
        print("📄 创建打包规格文件...")
        
        # 收集数据文件
        data_files = []
        
        # 样式文件
        for style_file in ['style.qss', 'style_dark.qss']:
            if os.path.exists(style_file):
                data_files.append(f"('{style_file}', '.')")
        
        # 配置文件
        if os.path.exists('config.json'):
            data_files.append("('config.json', '.')")
        
        # 文档文件
        docs = ['API配置指南.md', '流程优化总结.md', '部署指南.md']
        for doc in docs:
            if os.path.exists(doc):
                data_files.append(f"('{doc}', '.')")
        
        data_files_str = '[' + ', '.join(data_files) + ']'
        
        # 创建规格文件内容
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# 数据文件
datas = {data_files_str}

# 隐藏导入 - 包含所有必要的模块
hiddenimports = [
    # PyQt5 核心
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.sip',
    
    # WebSocket 完整支持
    'websocket',
    'websocket._core',
    'websocket._app',
    'websocket._socket',
    'websocket._http',
    'websocket._handshake',
    'websocket._url',
    'websocket._utils',
    'websocket._exceptions',
    'websocket._logging',
    
    # 网络和HTTP
    'requests',
    'requests.adapters',
    'requests.auth',
    'requests.cookies',
    'requests.models',
    'requests.sessions',
    'urllib3',
    'urllib3.util.retry',
    'ssl',
    'socket',
    
    # 音视频处理
    'pydub',
    'pydub.audio_segment',
    'pydub.effects',
    'moviepy.editor',
    
    # 数据处理
    'numpy',
    'json',
    'base64',
    'hashlib',
    'threading',
    'queue',
    'concurrent.futures',
    'langdetect',
    
    # 系统模块
    'os',
    'sys',
    'pathlib',
    'tempfile',
    'shutil',
    'subprocess',
    'time',
    'datetime',
    'collections',
    'functools',
    're'
]

a = Analysis(
    ['{self.main_script}'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # 排除不需要的大型库
        'scipy',
        'pandas',
        'tkinter',
        '_tkinter',
        'test'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{self.project_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
        
        spec_filename = f'{self.project_name}.spec'
        with open(spec_filename, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✅ 规格文件已创建: {spec_filename}")
        return spec_filename
    
    def build_executable(self, spec_file):
        """构建可执行文件"""
        print("🚀 开始构建可执行文件...")
        print("   这可能需要几分钟时间，请耐心等待...")
        
        cmd = [
            'pyinstaller',
            '--clean',
            '--noconfirm',
            spec_file
        ]
        
        try:
            # 运行构建命令
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True
            )
            
            # 实时显示关键信息
            for line in process.stdout:
                if any(keyword in line for keyword in ['INFO:', 'ERROR:', 'WARNING:']):
                    if 'INFO: Building EXE' in line:
                        print("   📦 正在构建EXE文件...")
                    elif 'completed successfully' in line:
                        print("   ✅ 构建步骤完成")
                    elif 'ERROR:' in line:
                        print(f"   ❌ 错误: {line.strip()}")
                    elif 'WARNING:' in line and 'not found' in line:
                        print(f"   ⚠️ 警告: {line.strip()}")
            
            process.wait()
            
            if process.returncode == 0:
                print("✅ 可执行文件构建成功!")
                return True
            else:
                print("❌ 构建失败")
                return False
                
        except Exception as e:
            print(f"❌ 构建过程中发生错误: {e}")
            return False
    
    def create_release_package(self):
        """创建发布包"""
        print("📦 创建发布包...")
        
        # 检查生成的EXE文件
        exe_path = f'dist/{self.project_name}.exe'
        if not os.path.exists(exe_path):
            print(f"❌ 找不到生成的可执行文件: {exe_path}")
            return False
        
        # 创建发布目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 复制主程序
        shutil.copy(exe_path, self.output_dir)
        exe_size = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"   ✅ 复制主程序 ({exe_size:.1f} MB)")
        
        # 创建必要目录
        dirs_to_create = ['audio_cache', 'logs']
        for dir_name in dirs_to_create:
            os.makedirs(os.path.join(self.output_dir, dir_name), exist_ok=True)
        print("   ✅ 创建工作目录")
        
        # 复制文档
        docs = ['API配置指南.md', '流程优化总结.md', '部署指南.md']
        for doc in docs:
            if os.path.exists(doc):
                shutil.copy(doc, self.output_dir)
        print("   ✅ 复制文档文件")
        
        # 创建配置文件
        self.create_default_config()
        
        # 创建用户指南
        self.create_user_guide()
        
        print(f"✅ 发布包创建完成: {self.output_dir}/")
        return True
    
    def create_default_config(self):
        """创建默认配置文件"""
        default_config = {
            "xunfei_appid": "",
            "xunfei_apikey": "",
            "xunfei_apisecret": "",
            "xunfei_tts_appid": "",
            "xunfei_tts_apikey": "",
            "xunfei_tts_apisecret": "",
            "baidu_appid": "",
            "baidu_appkey": "",
            "voice_speed": 100,
            "voice_volume": 80,
            "voice_type": "xiaoyan",
            "output_quality": "高质量",
            "enable_cache": True,
            "concurrent_count": 1,
            "subtitle_mode": "硬字幕（烧录到视频）"
        }
        
        config_path = os.path.join(self.output_dir, 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        print("   ✅ 创建默认配置文件")
    
    def create_user_guide(self):
        """创建用户指南"""
        guide_content = f'''# {self.project_name} - 用户指南

## 🚀 快速开始

1. **启动程序**
   双击 {self.project_name}.exe 启动程序

2. **配置API**
   - 点击菜单栏的"设置"
   - 分别配置科大讯飞和百度的API密钥
   - 保存设置

3. **开始转换**
   - 选择视频文件
   - 选择输出目录
   - 选择转换类型
   - 点击"开始转换"

## ⚙️ 系统要求

- Windows 7/8/10/11 (64位)
- 网络连接（调用在线API）
- 2GB+ 内存
- 1GB+ 硬盘空间

## 🔑 API配置

### 科大讯飞语音转写API (STT)
- 用于将视频中的语音转为文字
- 需要: APPID、APIKey、APISecret

### 科大讯飞语音合成API (TTS)  
- 用于将文字转为新的语音
- 需要: APPID、APIKey、APISecret

### 百度翻译API
- 用于中英文翻译
- 需要: APPID、AppKey

详细配置步骤请参考 API配置指南.md

## 📁 文件说明

- {self.project_name}.exe - 主程序
- audio_cache/ - 音频缓存目录
- logs/ - 日志文件目录
- config.json - 配置文件
- API配置指南.md - 详细配置说明

## ❗ 注意事项

- 首次启动可能较慢（正在解压程序）
- 确保网络连接稳定
- API配置必须正确
- 处理大文件时需要耐心等待

## 🐛 常见问题

**Q: 程序无法启动？**
A: 检查Windows版本是否为64位，关闭杀毒软件重试

**Q: 提示网络错误？**  
A: 检查网络连接和API配置是否正确

**Q: 处理很慢？**
A: 启用音频缓存，选择合适的并发处理数

**Q: 生成的视频没有声音？**
A: 检查原视频是否有音轨，API配置是否正确

---
版本: v1.0 | 构建时间: {datetime.datetime.now().strftime("%Y-%m-%d")}
'''
        
        guide_path = os.path.join(self.output_dir, '用户指南.txt')
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)
        print("   ✅ 创建用户指南")
    
    def print_summary(self):
        """打印构建总结"""
        print()
        print("=" * 60)
        print("🎉 打包完成!")
        print("=" * 60)
        print(f"📁 发布包位置: {os.path.abspath(self.output_dir)}")
        print(f"🎯 主程序: {self.output_dir}/{self.project_name}.exe")
        print()
        print("📋 包含文件:")
        if os.path.exists(self.output_dir):
            for item in os.listdir(self.output_dir):
                item_path = os.path.join(self.output_dir, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path) / 1024
                    print(f"   📄 {item} ({size:.1f} KB)")
                else:
                    print(f"   📁 {item}/")
        print()
        print("✅ 此版本包含所有依赖，用户无需安装Python环境")
        print("💡 可直接将整个文件夹分发给用户使用")
        print("=" * 60)
    
    def build(self):
        """执行完整的构建流程"""
        import datetime
        
        self.print_banner()
        
        # 1. 检查环境
        if not self.check_environment():
            print("❌ 环境检查失败，构建终止")
            return False
        
        # 2. 安装依赖
        if not self.install_dependencies():
            print("❌ 依赖安装失败，构建终止")
            return False
        
        # 3. 清理旧文件
        self.clean_build_dirs()
        
        # 4. 创建规格文件
        spec_file = self.create_spec_file()
        
        # 5. 构建可执行文件
        if not self.build_executable(spec_file):
            print("❌ 可执行文件构建失败，构建终止")
            return False
        
        # 6. 创建发布包
        if not self.create_release_package():
            print("❌ 发布包创建失败，构建终止")
            return False
        
        # 7. 打印总结
        self.print_summary()
        
        return True

def main():
    """主函数"""
    builder = PackageBuilder()
    success = builder.build()
    
    print()
    if success:
        print("🎊 构建成功完成！")
    else:
        print("💥 构建失败，请检查错误信息")
    
    input("按回车键退出...")
    return success

if __name__ == "__main__":
    main() 