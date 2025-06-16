# -*- coding: utf-8 -*-
"""
增强版语音替换工具UI v3.1 (UI优化版)
- 现代化视觉设计与布局
- 完整的文件拖拽支持
- 优雅的线程停止机制
- 样式与逻辑分离
- 自由缩放功能
- 增强的滑块控件
- 图标支持
"""

import sys
import os
import json
import time
import threading
import subprocess
from pathlib import Path

# 设置控制台编码为UTF-8，解决中文乱码问题
if sys.platform.startswith('win'):
    import locale
    try:
        # 尝试设置控制台编码
        os.system('chcp 65001 > nul')
        # 设置Python的默认编码
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception as e:
        print(f"设置编码时出错: {e}")

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 导入原有功能模块
import addNewSound
import video_to_txt
import syntheticSpeech
import syntheticSpeechCn
import syntheticSpeechTranslateToEn
import syntheticSpeechTranslateToCn
import generateWav
import batch_processor
import app_icon

# --- 统一路径管理器 ---
class SubtitlePathManager:
    """统一的字幕路径管理器 - 确保所有字幕相关路径的一致性"""
    
    def __init__(self, base_path, video_filename=None):
        self.base_path = os.path.abspath(base_path).replace('\\', '/')
        self.temp_files = []  # 跟踪临时文件
        
        # 生成唯一的文件前缀，避免批量处理时的文件名冲突
        if video_filename:
            # 使用视频文件名作为前缀
            self.file_prefix = os.path.splitext(os.path.basename(video_filename))[0]
        else:
            # 使用时间戳作为后备方案
            import time
            self.file_prefix = f"video_{int(time.time())}"
        
        # 清理文件前缀，移除特殊字符
        import re
        self.file_prefix = re.sub(r'[^\w\-_]', '_', self.file_prefix)
        
    def get_original_subtitle_path(self):
        """获取原始字幕文件路径"""
        return os.path.join(self.base_path, f'{self.file_prefix}_subtitle.srt').replace('\\', '/')
    
    def get_translated_subtitle_path(self, conversion_suffix):
        """获取翻译后字幕文件路径"""
        return os.path.join(self.base_path, f'{self.file_prefix}_subtitle_{conversion_suffix}.srt').replace('\\', '/')
    
    def get_audio_path(self):
        """获取提取的音频文件路径"""
        return os.path.join(self.base_path, f'{self.file_prefix}_extractedAudio.wav').replace('\\', '/')
    
    def get_video_without_audio_path(self):
        """获取无声视频文件路径"""
        return os.path.join(self.base_path, f'{self.file_prefix}_videoWithoutAudio.mp4').replace('\\', '/')
    
    def get_output_video_path(self, base_name, conversion_suffix):
        """获取输出视频文件路径"""
        name, ext = os.path.splitext(base_name)
        return os.path.join(self.base_path, f"{name}_{conversion_suffix}{ext}").replace('\\', '/')
    
    def get_temp_file_path(self, filename):
        """获取临时文件路径并跟踪"""
        # 为临时文件也添加前缀
        base_name, ext = os.path.splitext(filename)
        temp_filename = f"{self.file_prefix}_{base_name}{ext}"
        temp_path = os.path.join(self.base_path, temp_filename).replace('\\', '/')
        self.temp_files.append(temp_path)
        return temp_path
    
    def get_extracted_audio_filename(self):
        """获取提取音频的文件名"""
        return f'{self.file_prefix}_extractedAudio.wav'
    
    def get_original_subtitle_filename(self):
        """获取原始字幕的文件名"""
        return f'{self.file_prefix}_subtitle.srt'
    
    def get_silent_video_filename(self):
        """获取无声视频的文件名"""
        return f'{self.file_prefix}_videoWithoutAudio.mp4'
    
    def ensure_directory_exists(self):
        """确保基础目录存在"""
        try:
            os.makedirs(self.base_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败 {self.base_path}: {e}")
            return False
    
    def validate_file_exists(self, file_path, file_description="文件"):
        """验证文件是否存在"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_description}不存在: {file_path}")
        return True
    
    def cleanup_temp_files(self):
        """清理所有临时文件"""
        cleaned_count = 0
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    cleaned_count += 1
                    print(f"已清理临时文件: {temp_file}")
            except Exception as e:
                print(f"清理临时文件失败 {temp_file}: {e}")
        
        self.temp_files.clear()
        print(f"临时文件清理完成，共清理 {cleaned_count} 个文件")
    
    def get_file_info(self, file_path):
        """获取文件信息"""
        try:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                return {
                    'exists': True,
                    'size': size,
                    'size_mb': size / (1024 * 1024),
                    'path': file_path
                }
            else:
                return {'exists': False, 'path': file_path}
        except Exception as e:
            return {'exists': False, 'error': str(e), 'path': file_path}

# --- 增强的文件操作工具类 ---
class FileOperationHelper:
    """文件操作辅助类 - 增强错误处理和编码支持"""
    
    @staticmethod
    def read_subtitle_file(file_path):
        """安全读取字幕文件，支持多种编码"""
        encodings = ['utf-8', 'gbk', 'windows-1252', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"成功使用 {encoding} 编码读取字幕文件: {file_path}")
                return content, encoding
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"读取文件时出错 ({encoding}): {e}")
                continue
        
        raise Exception(f"无法读取字幕文件 {file_path}，尝试了所有编码格式: {encodings}")
    
    @staticmethod
    def write_subtitle_file(file_path, content, encoding='utf-8'):
        """安全写入字幕文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            print(f"成功写入字幕文件: {file_path}")
            return True
        except Exception as e:
            print(f"写入字幕文件失败 {file_path}: {e}")
            return False
    
    @staticmethod
    def safe_file_operation(operation, *args, **kwargs):
        """安全的文件操作包装器"""
        try:
            return operation(*args, **kwargs)
        except FileNotFoundError as e:
            print(f"文件未找到: {e}")
            raise
        except PermissionError as e:
            print(f"权限错误: {e}")
            raise
        except Exception as e:
            print(f"文件操作失败: {e}")
            raise

# --- 自定义增强滑块组件 ---
class EnhancedSlider(QWidget):
    """增强的滑块组件，支持箭头调节和双击输入"""
    valueChanged = pyqtSignal(int)
    
    def __init__(self, minimum=0, maximum=100, value=50, step=5, suffix="%", parent=None):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.suffix = suffix
        self.current_value = value
        
        self.setupUI()
        
    def setupUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 减少按钮
        self.decrease_btn = QPushButton()
        self.decrease_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowLeft))
        self.decrease_btn.setFixedSize(24, 24)
        self.decrease_btn.setToolTip(f"减少 {self.step}{self.suffix}")
        self.decrease_btn.clicked.connect(self.decreaseValue)
        
        # 滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(self.minimum, self.maximum)
        self.slider.setValue(self.current_value)
        self.slider.valueChanged.connect(self.onSliderChanged)
        
        # 增加按钮
        self.increase_btn = QPushButton()
        self.increase_btn.setIcon(self.style().standardIcon(QStyle.SP_ArrowRight))
        self.increase_btn.setFixedSize(24, 24)
        self.increase_btn.setToolTip(f"增加 {self.step}{self.suffix}")
        self.increase_btn.clicked.connect(self.increaseValue)
        
        # 数值标签（支持双击输入）
        self.value_label = QLabel(f"{self.current_value}{self.suffix}")
        self.value_label.setFixedWidth(50)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-weight: bold; color: #0078D7; font-size: 12px;")
        self.value_label.setToolTip("双击输入自定义数值")
        
        # 安装事件过滤器以支持双击
        self.value_label.installEventFilter(self)
        
        layout.addWidget(self.decrease_btn)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.increase_btn)
        layout.addWidget(self.value_label)
        
    def eventFilter(self, obj, event):
        if obj == self.value_label and event.type() == QEvent.MouseButtonDblClick:
            self.openInputDialog()
            return True
        return super().eventFilter(obj, event)
    
    def openInputDialog(self):
        """打开输入对话框"""
        value, ok = QInputDialog.getInt(
            self, "输入数值", 
            f"请输入数值 ({self.minimum}-{self.maximum}):", 
            self.current_value, self.minimum, self.maximum
        )
        if ok:
            self.setValue(value)
    
    def decreaseValue(self):
        new_value = max(self.minimum, self.current_value - self.step)
        self.setValue(new_value)
    
    def increaseValue(self):
        new_value = min(self.maximum, self.current_value + self.step)
        self.setValue(new_value)
    
    def onSliderChanged(self, value):
        self.setValue(value)
    
    def setValue(self, value):
        value = max(self.minimum, min(self.maximum, value))
        self.current_value = value
        self.slider.setValue(value)
        self.value_label.setText(f"{value}{self.suffix}")
        self.valueChanged.emit(value)
    
    def value(self):
        return self.current_value

# --- 缩放管理器 ---
class ZoomManager(QObject):
    """UI缩放管理器 - 全面缩放实现"""
    zoomChanged = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_factor = 1.0
        self.min_zoom = 0.8
        self.max_zoom = 1.4
        self.base_font_size = 9
        
    def setZoom(self, factor):
        """设置缩放因子"""
        factor = max(self.min_zoom, min(self.max_zoom, factor))
        if abs(factor - self.zoom_factor) > 0.01:
            self.zoom_factor = factor
            self.zoomChanged.emit(factor)
    
    def zoomIn(self):
        """放大"""
        new_factor = min(self.max_zoom, self.zoom_factor + 0.1)
        self.setZoom(new_factor)
    
    def zoomOut(self):
        """缩小"""
        new_factor = max(self.min_zoom, self.zoom_factor - 0.1)
        self.setZoom(new_factor)
    
    def resetZoom(self):
        """重置缩放"""
        self.setZoom(1.0)
    
    def getZoom(self):
        return self.zoom_factor

# --- NEW: 自定义文件输入组件，增强UX ---
class FileInputWidget(QWidget):
    """一个支持拖拽和点击选择文件的自定义组件"""
    pathChanged = pyqtSignal(str)

    def __init__(self, description="拖拽视频文件至此，或点击浏览"):
        super().__init__()
        self.setAcceptDrops(True)
        self.description = description
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 添加图标和文本的容器
        content_layout = QHBoxLayout()
        
        # 添加文件图标 - 使用简单的文件图标
        icon_label = QLabel()
        file_icon = self.style().standardIcon(QStyle.SP_FileIcon)
        icon_label.setPixmap(file_icon.pixmap(32, 32))
        icon_label.setAlignment(Qt.AlignCenter)
        
        self.path_label = QLabel(self.description)
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setObjectName("dropAreaLabel")
        
        content_layout.addWidget(icon_label)
        content_layout.addWidget(self.path_label, 1)
        
        layout.addLayout(content_layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            event.acceptProposedAction()
            self.path_label.setText("📥 可以松开鼠标了...")
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.path_label.setText(self.description)

    def dropEvent(self, event: QDropEvent):
        url = event.mimeData().urls()[0]
        path = url.toLocalFile()
        if os.path.isfile(path):
            self.set_path(path)
        self.path_label.setText(self.description)

    def mousePressEvent(self, event: QMouseEvent):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*)"
        )
        if file_path:
            self.set_path(file_path)

    def set_path(self, path):
        self.path_label.setText(os.path.basename(path))
        self.pathChanged.emit(path)

class VideoPreviewDialog(QDialog):
    """视频预览对话框"""
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setupUI()
        self.loadVideoInfo()
    
    def setupUI(self):
        self.setWindowTitle("视频预览")
        self.setModal(True)
        self.resize(550, 450)  # 从600x500调整为550x450
        
        layout = QVBoxLayout(self)
        
        # 视频信息显示
        info_group = QGroupBox("视频信息")
        info_layout = QFormLayout(info_group)
        
        self.file_name_label = QLabel()
        self.duration_label = QLabel()
        self.size_label = QLabel()
        self.resolution_label = QLabel()
        self.fps_label = QLabel()
        
        info_layout.addRow("文件名:", self.file_name_label)
        info_layout.addRow("时长:", self.duration_label)
        info_layout.addRow("文件大小:", self.size_label)
        info_layout.addRow("分辨率:", self.resolution_label)
        info_layout.addRow("帧率:", self.fps_label)
        
        # 音频信息
        audio_group = QGroupBox("音频信息")
        audio_layout = QFormLayout(audio_group)
        
        self.audio_codec_label = QLabel()
        self.sample_rate_label = QLabel()
        self.channels_label = QLabel()
        
        audio_layout.addRow("音频编码:", self.audio_codec_label)
        audio_layout.addRow("采样率:", self.sample_rate_label)
        audio_layout.addRow("声道数:", self.channels_label)
        
        # 预览区域
        preview_group = QGroupBox("预览选项")
        preview_layout = QVBoxLayout(preview_group)
        
        preview_text = QLabel("当前选择的转换设置:")
        self.preview_info = QLabel()
        self.preview_info.setWordWrap(True)
        self.preview_info.setStyleSheet("padding: 10px; border: 1px solid #ccc; border-radius: 4px; background: #f8f9fa;")
        
        # 按钮
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton("在文件管理器中打开")
        self.close_btn = QPushButton("关闭")
        
        self.open_btn.clicked.connect(self.openInExplorer)
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.open_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        
        preview_layout.addWidget(preview_text)
        preview_layout.addWidget(self.preview_info)
        
        layout.addWidget(info_group)
        layout.addWidget(audio_group)
        layout.addWidget(preview_group)
        layout.addLayout(btn_layout)
    
    def loadVideoInfo(self):
        """加载视频信息"""
        try:
            import os
            from moviepy.editor import VideoFileClip
            
            # 基本文件信息
            file_name = os.path.basename(self.video_path)
            file_size = os.path.getsize(self.video_path)
            size_mb = file_size / (1024 * 1024)
            
            self.file_name_label.setText(file_name)
            self.size_label.setText(f"{size_mb:.1f} MB")
            
            # 视频信息
            try:
                with VideoFileClip(self.video_path) as clip:
                    duration = clip.duration
                    fps = clip.fps if clip.fps else "未知"
                    resolution = f"{clip.w}x{clip.h}" if clip.w and clip.h else "未知"
                    
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    self.duration_label.setText(f"{minutes}:{seconds:02d}")
                    self.resolution_label.setText(resolution)
                    self.fps_label.setText(f"{fps} FPS" if fps != "未知" else fps)
                    
                    # 音频信息
                    if clip.audio:
                        audio_fps = clip.audio.fps if hasattr(clip.audio, 'fps') else "未知"
                        channels = clip.audio.nchannels if hasattr(clip.audio, 'nchannels') else "未知"
                        
                        self.sample_rate_label.setText(f"{audio_fps} Hz" if audio_fps != "未知" else audio_fps)
                        self.channels_label.setText(f"{channels} 声道" if channels != "未知" else channels)
                        self.audio_codec_label.setText("PCM/WAV")
                    else:
                        self.sample_rate_label.setText("无音频轨道")
                        self.channels_label.setText("无音频轨道")
                        self.audio_codec_label.setText("无音频轨道")
                        
            except Exception as e:
                self.duration_label.setText("无法获取")
                self.resolution_label.setText("无法获取")
                self.fps_label.setText("无法获取")
                self.sample_rate_label.setText("无法获取")
                self.channels_label.setText("无法获取")
                self.audio_codec_label.setText("无法获取")
                
            # 获取父窗口的转换设置
            if hasattr(self.parent(), 'conversion_combo'):
                conversion_type = self.parent().conversion_combo.currentText()
                voice_type = self.parent().voice_combo.currentText()
                speed = self.parent().speed_slider.value()
                volume = self.parent().volume_slider.value()
                quality = self.parent().quality_combo.currentText()
                
                # 获取预计时间
                estimated_time = self.parent().calculateEstimatedTime()
                
                preview_text = f"""
转换类型: {conversion_type}
发音人: {voice_type}
语速: {speed}%
音量: {volume}%
输出质量: {quality}

预计处理时间: {estimated_time}
                """.strip()
                self.preview_info.setText(preview_text)
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取视频信息: {str(e)}")
    
    def openInExplorer(self):
        """在文件管理器中打开文件"""
        try:
            import os
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                subprocess.run(f'explorer /select,"{self.video_path}"', shell=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", self.video_path])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(self.video_path)])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件管理器: {str(e)}")


class SettingsDialog(QDialog):
    """设置对话框 (代码结构优化)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        self.loadSettings()
    
    def extractDefaultConfigs(self):
        """从项目文件中提取默认API配置"""
        default_configs = {
            'xunfei_appid': 'c9f38a98',  # 来自video_to_txt.py
            'xunfei_apikey': '5cc4877fa4b7d173d8f1c085e50a4788',  # 来自其他模块
            'xunfei_apisecret': 'a8b81c43d2528e7edcd6a826ec31ee19',  # 来自video_to_txt.py
            'baidu_appid': '20240510002047252',  # 来自Baidu_Text_transAPI.py
            'baidu_appkey': 'kTWYriLuEEEKr0BE70d1',  # 来自Baidu_Text_transAPI.py
        }
        return default_configs
    
    # ... (设置对话框的UI部分基本不变, 此处省略以保持简洁)
    # ... (您可以从原文件中复制SettingsDialog的setupUi方法)
    def setupUi(self):
        self.setWindowTitle("设置")
        self.setFixedSize(550, 480)  # 从600x550调整为550x480，更紧凑
        layout = QVBoxLayout()
        
        # 创建选项卡控件
        tab_widget = QTabWidget()
        
        # API设置选项卡
        api_tab = QWidget()
        api_layout = QFormLayout()
        
        self.xunfei_appid = QLineEdit()
        self.xunfei_apikey = QLineEdit()
        self.xunfei_apisecret = QLineEdit()
        self.xunfei_apisecret.setEchoMode(QLineEdit.Password)
        
        self.baidu_appid = QLineEdit()
        self.baidu_appkey = QLineEdit()
        self.baidu_appkey.setEchoMode(QLineEdit.Password)
        
        api_layout.addRow("科大讯飞 APPID:", self.xunfei_appid)
        api_layout.addRow("科大讯飞 APIKey:", self.xunfei_apikey)
        api_layout.addRow("科大讯飞 APISecret:", self.xunfei_apisecret)
        api_layout.addRow(QLabel()) # 分隔线
        api_layout.addRow("百度翻译 APPID:", self.baidu_appid)
        api_layout.addRow("百度翻译 AppKey:", self.baidu_appkey)
        
        api_tab.setLayout(api_layout)
        tab_widget.addTab(api_tab, "API 配置")
        
        # 语音设置选项卡
        voice_tab = QWidget()
        voice_layout = QFormLayout()
        
        # 语音参数设置
        self.voice_speed = QSlider(Qt.Horizontal)
        self.voice_speed.setRange(50, 200)
        self.voice_speed.setValue(100)
        self.voice_speed_label = QLabel("100")
        self.voice_speed.valueChanged.connect(lambda v: self.voice_speed_label.setText(str(v)))
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.voice_speed)
        speed_layout.addWidget(self.voice_speed_label)
        
        self.voice_volume = QSlider(Qt.Horizontal)
        self.voice_volume.setRange(0, 100)
        self.voice_volume.setValue(80)
        self.voice_volume_label = QLabel("80")
        self.voice_volume.valueChanged.connect(lambda v: self.voice_volume_label.setText(str(v)))
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.voice_volume)
        volume_layout.addWidget(self.voice_volume_label)
        
        self.voice_pitch = QSlider(Qt.Horizontal)
        self.voice_pitch.setRange(0, 100)
        self.voice_pitch.setValue(50)
        self.voice_pitch_label = QLabel("50")
        self.voice_pitch.valueChanged.connect(lambda v: self.voice_pitch_label.setText(str(v)))
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(self.voice_pitch)
        pitch_layout.addWidget(self.voice_pitch_label)
        
        # 发音人选择
        self.voice_type = QComboBox()
        self.voice_type.addItems([
            "xiaoyan - 小燕（女声）",
            "xiaoyu - 小宇（男声）", 
            "xiaoxin - 小欣（女声）",
            "aisxping - 小萍（女声）",
            "x4_EnUs_Laura_education - Laura（英文女声）",
            "x4_EnUs_Emma_education - Emma（英文女声）",
            "x4_EnUs_Alex_education - Alex（英文男声）"
        ])
        
        # 输出质量
        self.output_quality = QComboBox()
        self.output_quality.addItems(["标准质量", "高质量", "超清质量"])
        self.output_quality.setCurrentText("高质量")
        
        voice_layout.addRow("语速 (50-200):", speed_layout)
        voice_layout.addRow("音量 (0-100):", volume_layout)
        voice_layout.addRow("音调 (0-100):", pitch_layout)
        voice_layout.addRow("发音人:", self.voice_type)
        voice_layout.addRow("输出质量:", self.output_quality)
        
        voice_tab.setLayout(voice_layout)
        tab_widget.addTab(voice_tab, "语音设置")
        
        # 应用设置选项卡
        app_tab = QWidget()
        app_layout = QFormLayout()
        
        self.auto_save = QCheckBox("自动保存配置")
        self.auto_save.setChecked(True)
        
        self.enable_cache = QCheckBox("启用音频缓存")
        self.enable_cache.setChecked(True)
        
        self.concurrent_count = QSpinBox()
        self.concurrent_count.setRange(1, 4)
        self.concurrent_count.setValue(1)
        
        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText("INFO")
        
        app_layout.addRow("自动保存:", self.auto_save)
        app_layout.addRow("音频缓存:", self.enable_cache)
        app_layout.addRow("并发处理数:", self.concurrent_count)
        app_layout.addRow("日志级别:", self.log_level)
        
        app_tab.setLayout(app_layout)
        tab_widget.addTab(app_tab, "应用设置")
        
        # 按钮
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("导出配置")
        import_btn = QPushButton("导入配置")
        reset_btn = QPushButton("重置默认")
        
        export_btn.clicked.connect(self.exportSettings)
        import_btn.clicked.connect(self.importSettings)
        reset_btn.clicked.connect(self.resetSettings)
        
        button_layout.addWidget(export_btn)
        button_layout.addWidget(import_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self.saveSettings)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(tab_widget)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def loadSettings(self):
        """加载设置"""
        # 首先获取默认配置
        default_configs = self.extractDefaultConfigs()
        
        # MODIFIED: 增加更具体的异常捕获，避免静默失败
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 如果config.json存在，优先使用其中的配置，否则使用默认配置
                    self.xunfei_appid.setText(settings.get('xunfei_appid', default_configs['xunfei_appid']))
                    self.xunfei_apikey.setText(settings.get('xunfei_apikey', default_configs['xunfei_apikey']))
                    self.xunfei_apisecret.setText(settings.get('xunfei_apisecret', default_configs['xunfei_apisecret']))
                    self.baidu_appid.setText(settings.get('baidu_appid', default_configs['baidu_appid']))
                    self.baidu_appkey.setText(settings.get('baidu_appkey', default_configs['baidu_appkey']))
            else:
                # 如果config.json不存在，直接使用默认配置
                self.xunfei_appid.setText(default_configs['xunfei_appid'])
                self.xunfei_apikey.setText(default_configs['xunfei_apikey'])
                self.xunfei_apisecret.setText(default_configs['xunfei_apisecret'])
                self.baidu_appid.setText(default_configs['baidu_appid'])
                self.baidu_appkey.setText(default_configs['baidu_appkey'])
        except (IOError, json.JSONDecodeError) as e:
            QMessageBox.warning(self, "加载错误", f"无法加载配置文件 'config.json':\n{e}")
            # 发生错误时也使用默认配置
            self.xunfei_appid.setText(default_configs['xunfei_appid'])
            self.xunfei_apikey.setText(default_configs['xunfei_apikey'])
            self.xunfei_apisecret.setText(default_configs['xunfei_apisecret'])
            self.baidu_appid.setText(default_configs['baidu_appid'])
            self.baidu_appkey.setText(default_configs['baidu_appkey'])

    def saveSettings(self):
        """保存设置"""
        settings = {
            # API 配置
            'xunfei_appid': self.xunfei_appid.text(),
            'xunfei_apikey': self.xunfei_apikey.text(),
            'xunfei_apisecret': self.xunfei_apisecret.text(),
            'baidu_appid': self.baidu_appid.text(),
            'baidu_appkey': self.baidu_appkey.text(),
            # 语音设置
            'voice_speed': self.voice_speed.value(),
            'voice_volume': self.voice_volume.value(),
            'voice_pitch': self.voice_pitch.value(),
            'voice_type': self.voice_type.currentText().split(' - ')[0],  # 提取发音人代码
            'output_quality': self.output_quality.currentText(),
            # 应用设置
            'auto_save': self.auto_save.isChecked(),
            'enable_cache': self.enable_cache.isChecked(),
            'concurrent_count': self.concurrent_count.value(),
            'log_level': self.log_level.currentText(),
        }
        
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            QMessageBox.information(self, "提示", "设置保存成功！")
            self.accept()
        except IOError as e:
            QMessageBox.critical(self, "保存错误", f"无法保存配置文件 'config.json':\n{e}")
    
    def exportSettings(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "config_backup.json", "JSON 文件 (*.json)"
        )
        if file_path:
            try:
                settings = {
                    'xunfei_appid': self.xunfei_appid.text(),
                    'xunfei_apikey': self.xunfei_apikey.text(),
                    'xunfei_apisecret': self.xunfei_apisecret.text(),
                    'baidu_appid': self.baidu_appid.text(),
                    'baidu_appkey': self.baidu_appkey.text(),
                    'voice_speed': self.voice_speed.value(),
                    'voice_volume': self.voice_volume.value(),
                    'voice_pitch': self.voice_pitch.value(),
                    'voice_type': self.voice_type.currentText().split(' - ')[0],
                    'output_quality': self.output_quality.currentText(),
                    'auto_save': self.auto_save.isChecked(),
                    'enable_cache': self.enable_cache.isChecked(),
                    'concurrent_count': self.concurrent_count.value(),
                    'log_level': self.log_level.currentText(),
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "提示", "配置导出成功！")
            except Exception as e:
                QMessageBox.critical(self, "导出错误", f"导出配置失败：{str(e)}")
    
    def importSettings(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "JSON 文件 (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 更新界面
                self.xunfei_appid.setText(settings.get('xunfei_appid', ''))
                self.xunfei_apikey.setText(settings.get('xunfei_apikey', ''))
                self.xunfei_apisecret.setText(settings.get('xunfei_apisecret', ''))
                self.baidu_appid.setText(settings.get('baidu_appid', ''))
                self.baidu_appkey.setText(settings.get('baidu_appkey', ''))
                
                self.voice_speed.setValue(settings.get('voice_speed', 100))
                self.voice_volume.setValue(settings.get('voice_volume', 80))
                self.voice_pitch.setValue(settings.get('voice_pitch', 50))
                
                voice_type = settings.get('voice_type', 'xiaoyan')
                for i in range(self.voice_type.count()):
                    if self.voice_type.itemText(i).startswith(voice_type):
                        self.voice_type.setCurrentIndex(i)
                        break
                
                quality = settings.get('output_quality', '高质量')
                self.output_quality.setCurrentText(quality)
                
                self.auto_save.setChecked(settings.get('auto_save', True))
                self.enable_cache.setChecked(settings.get('enable_cache', True))
                self.concurrent_count.setValue(settings.get('concurrent_count', 1))
                self.log_level.setCurrentText(settings.get('log_level', 'INFO'))
                
                QMessageBox.information(self, "提示", "配置导入成功！")
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入配置失败：{str(e)}")
    
    def resetSettings(self):
        """重置为默认设置"""
        reply = QMessageBox.question(
            self, "确认重置", "确定要重置为默认设置吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 重置API配置为默认值
            defaults = self.extractDefaultConfigs()
            self.xunfei_appid.setText(defaults['xunfei_appid'])
            self.xunfei_apikey.setText(defaults['xunfei_apikey'])
            self.xunfei_apisecret.setText(defaults['xunfei_apisecret'])
            self.baidu_appid.setText(defaults['baidu_appid'])
            self.baidu_appkey.setText(defaults['baidu_appkey'])
            
            # 重置语音设置
            self.voice_speed.setValue(100)
            self.voice_volume.setValue(80)
            self.voice_pitch.setValue(50)
            self.voice_type.setCurrentIndex(0)
            self.output_quality.setCurrentText("高质量")
            
            # 重置应用设置
            self.auto_save.setChecked(True)
            self.enable_cache.setChecked(True)
            self.concurrent_count.setValue(1)
            self.log_level.setCurrentText("INFO")

class ProcessThread(QThread):
    """处理线程"""
    progress = pyqtSignal(int, str) # NEW: 进度信号同时传递文本
    finished = pyqtSignal(bool, str)
    subtitle_ready = pyqtSignal(str, str)  # 新增：字幕准备信号(字幕内容, 类型)
    
    def __init__(self, video_path, save_path, conversion_type, voice_params=None):
        super().__init__()
        self.video_path = video_path
        self.save_path = save_path
        self.conversion_type = conversion_type
        self.voice_params = voice_params or {}
        # NEW: 线程安全停止标志位
        self._is_running = True
        
        # 初始化路径管理器和文件操作助手 - 传递视频文件名以生成唯一前缀
        self.path_manager = SubtitlePathManager(save_path, video_path)
        self.file_helper = FileOperationHelper()
    
    def detectLanguage(self, text):
        """检测文本语言（改进版）- 更准确的中英文识别"""
        if not text:
            return "unknown"
        
        # 清理文本，去除数字、标点符号、时间戳等
        import re
        clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', text)
        clean_text = re.sub(r'^\d+\n', '', clean_text, flags=re.MULTILINE)
        clean_text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', clean_text)
        clean_text = ' '.join(clean_text.split())  # 规范化空格
        
        if not clean_text:
            return "unknown"
        
        print(f"检测文本内容: {clean_text[:200]}...")  # 调试日志
        
        # 检测中文字符（包括中文标点）
        chinese_chars = sum(1 for char in clean_text if '\u4e00' <= char <= '\u9fff')
        
        # 检测英文字符（只计算字母）
        english_chars = sum(1 for char in clean_text if char.isascii() and char.isalpha())
        
        # 检测常见英文单词（扩展词汇表）
        english_words = [
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 
            'this', 'that', 'is', 'are', 'was', 'were', 'will', 'have', 'has', 'had', 
            'do', 'does', 'did', 'can', 'could', 'should', 'would', 'may', 'might', 
            'must', 'shall', 'from', 'up', 'out', 'about', 'into', 'over', 'under',
            'you', 'your', 'we', 'our', 'they', 'their', 'he', 'she', 'it', 'his', 'her',
            'what', 'when', 'where', 'why', 'how', 'who', 'which', 'there', 'here',
            'now', 'then', 'today', 'tomorrow', 'yesterday', 'time', 'day', 'year',
            'good', 'bad', 'big', 'small', 'new', 'old', 'first', 'last', 'long', 'short',
            'right', 'left', 'high', 'low', 'hot', 'cold', 'fast', 'slow', 'easy', 'hard'
        ]
        
        # 检测英文单词出现次数
        text_lower = clean_text.lower()
        english_word_count = sum(1 for word in english_words if f' {word} ' in f' {text_lower} ')
        
        # 检测常见中文词汇
        chinese_words = [
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
            '好', '自己', '这', '那', '什么', '时候', '可以', '现在', '知道', '这个',
            '我们', '他们', '她们', '这样', '那样', '因为', '所以', '但是', '如果'
        ]
        
        chinese_word_count = sum(1 for word in chinese_words if word in clean_text)
        
        total_chars = chinese_chars + english_chars
        
        print(f"语言检测统计:")
        print(f"  中文字符: {chinese_chars}")
        print(f"  英文字符: {english_chars}")
        print(f"  英文常用词: {english_word_count}")
        print(f"  中文常用词: {chinese_word_count}")
        print(f"  总字符数: {total_chars}")
        
        if total_chars == 0:
            return "unknown"
        
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        english_ratio = english_chars / total_chars if total_chars > 0 else 0
        
        # 改进的判断逻辑
        # 1. 如果有中文字符且中文词汇较多，判断为中文
        if chinese_chars > 0 and (chinese_word_count >= 2 or chinese_ratio > 0.2):
            print("检测结果: 中文")
            return "chinese"
        
        # 2. 如果英文单词较多或英文字符占主导，判断为英文
        if english_word_count >= 3 or (english_chars > chinese_chars and english_ratio > 0.5):
            print("检测结果: 英文")
            return "english"
        
        # 3. 混合文本的处理
        if chinese_chars > 0 and english_chars > 0:
            if chinese_chars > english_chars:
                print("检测结果: 中文（混合文本，中文占主导）")
                return "chinese"
            else:
                print("检测结果: 英文（混合文本，英文占主导）")
                return "english"
        
        # 4. 单纯基于字符数量判断
        if chinese_chars > english_chars:
            print("检测结果: 中文（基于字符数量）")
            return "chinese"
        elif english_chars > chinese_chars:
            print("检测结果: 英文（基于字符数量）")
            return "english"
        
        # 5. 默认情况
        print("检测结果: 未知，默认为中文")
        return "chinese"

    def run(self):
        try:
            # 确保输出目录存在
            if not self.path_manager.ensure_directory_exists():
                raise Exception(f"无法创建输出目录: {self.save_path}")
            
            # --- 步骤 1: 提取音频 ---
            if not self._is_running: return
            self.progress.emit(10, "正在提取音频...")
            
            # 使用路径管理器获取音频文件路径 - 传递自定义文件名
            expected_audio_path = self.path_manager.get_audio_path()
            wav_path = generateWav.run(
                self.video_path, 
                self.save_path,
                self.path_manager.get_extracted_audio_filename()
            )
            
            # 验证音频文件是否成功生成
            audio_info = self.path_manager.get_file_info(wav_path)
            if not audio_info['exists']:
                raise FileNotFoundError(f"音频提取失败，文件不存在: {wav_path}")
            
            print(f"音频文件已生成: {wav_path} ({audio_info['size_mb']:.2f}MB)")
            
            # --- 步骤 2: 生成无声视频 ---
            if not self._is_running: return
            self.progress.emit(20, "正在生成无声视频...")
            
            expected_video_path = self.path_manager.get_video_without_audio_path()
            video_without_sound = addNewSound.del_audio(
                self.video_path, 
                self.save_path,
                self.path_manager.get_silent_video_filename()
            )
            
            # 验证无声视频文件
            video_info = self.path_manager.get_file_info(video_without_sound)
            if not video_info['exists']:
                raise FileNotFoundError(f"无声视频生成失败: {video_without_sound}")
            
            print(f"无声视频已生成: {video_without_sound} ({video_info['size_mb']:.2f}MB)")
            
            # --- 步骤 3: 语音识别 ---
            if not self._is_running: return
            self.progress.emit(40, "正在识别语音，可能需要较长时间...")
            video_to_txt.run(
                wav_path, 
                self.save_path,
                self.path_manager.get_original_subtitle_filename()
            )
            
            # 使用路径管理器和文件助手读取原始字幕
            subtitle_file = self.path_manager.get_original_subtitle_path()
            original_text = ""
            
            try:
                self.path_manager.validate_file_exists(subtitle_file, "原始字幕文件")
                original_text, encoding = self.file_helper.read_subtitle_file(subtitle_file)
                print(f"原始字幕读取成功，编码: {encoding}, 长度: {len(original_text)} 字符")
                # 发送原始字幕到UI
                self.subtitle_ready.emit(original_text, "original")
            except Exception as e:
                print(f"读取原始字幕失败: {e}")
                raise Exception(f"语音识别结果读取失败: {e}")
            
            # 智能转换逻辑
            actual_conversion_type = self.conversion_type
            if self.conversion_type == "智能转换":
                if not self._is_running: return
                self.progress.emit(45, "正在分析语言...")
                detected_lang = self.detectLanguage(original_text)
                print(f"检测到的语言: {detected_lang}")
                
                if detected_lang == "chinese":
                    actual_conversion_type = "中文转英文"
                    print(f"智能转换: {detected_lang} -> {actual_conversion_type}")
                elif detected_lang == "english":
                    actual_conversion_type = "英文转中文"
                    print(f"智能转换: {detected_lang} -> {actual_conversion_type}")
                else:
                    actual_conversion_type = "英文转中文"  # 默认
                    print(f"智能转换: 未知语言，默认使用 {actual_conversion_type}")
            
            # --- 步骤 4: 合成新语音 ---
            if not self._is_running: return
            self.progress.emit(60, f"正在进行{actual_conversion_type}...")
            
            # 使用路径管理器生成输出文件路径
            base_name = os.path.basename(self.video_path)
            type_map = {
                "智能转换": "smart",
                "中文转英文": "cn_to_en", 
                "中文转中文": "cn_to_cn", 
                "英文转中文": "en_to_cn", 
                "英文转英文": "en_to_en"
            }
            conversion_suffix = type_map.get(actual_conversion_type, 'new')
            final_video_path = self.path_manager.get_output_video_path(base_name, conversion_suffix)

            # 传递语音参数
            voice_type = self.voice_params.get('voice_type', 'xiaoyan')
            speed = self.voice_params.get('speed', 100)
            volume = self.voice_params.get('volume', 80)
            quality = self.voice_params.get('quality', '高质量')

            # 根据转换类型处理并生成对应的字幕文件
            converted_subtitle_file = None
            generated_video_path = None
            
            print(f"开始语音合成，转换类型: {actual_conversion_type}")
            print(f"无声视频路径: {video_without_sound}")
            print(f"字幕文件路径: {subtitle_file}")
            print(f"预期输出路径: {final_video_path}")
            
            try:
                if actual_conversion_type == "中文转英文":
                    generated_video_path = syntheticSpeechTranslateToEn.run(video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume)
                    converted_subtitle_file = self.createTranslatedSubtitle(subtitle_file, "en", conversion_suffix)
                elif actual_conversion_type == "中文转中文":
                    generated_video_path = syntheticSpeechCn.run(video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume)
                    converted_subtitle_file = subtitle_file  # 中文到中文，字幕不变
                elif actual_conversion_type == "英文转中文":
                    generated_video_path = syntheticSpeechTranslateToCn.run(video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume)
                    converted_subtitle_file = self.createTranslatedSubtitle(subtitle_file, "zh", conversion_suffix)
                elif actual_conversion_type == "英文转英文":
                    generated_video_path = syntheticSpeech.run(video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume)
                    converted_subtitle_file = subtitle_file  # 英文到英文，字幕不变
                
                print(f"语音合成完成，返回路径: {generated_video_path}")
                
            except Exception as e:
                print(f"语音合成过程中发生错误: {e}")
                import traceback
                traceback.print_exc()
            
            # 验证和确定最终视频文件路径
            if generated_video_path and os.path.exists(generated_video_path):
                final_video_path = generated_video_path
                print(f"✅ 使用返回的视频路径: {final_video_path}")
            else:
                # 尝试查找可能的输出文件
                print(f"⚠️ 返回的路径无效，在 {self.save_path} 中搜索视频文件...")
                
                try:
                    files = os.listdir(self.save_path)
                    print(f"目录中所有文件: {files}")
                    
                    # 查找可能的视频文件
                    mp4_files = [f for f in files if f.endswith('.mp4')]
                    print(f"MP4文件: {mp4_files}")
                    
                    # 按优先级查找
                    base_name = os.path.splitext(os.path.basename(self.video_path))[0]
                    preferred_names = [
                        "NewVideo.mp4",
                        f"{base_name}_en_to_cn.mp4", 
                        f"{base_name}_cn_to_en.mp4",
                        f"{base_name}.mp4"
                    ]
                    
                    found_path = None
                    for name in preferred_names:
                        if name in mp4_files:
                            found_path = os.path.join(self.save_path, name).replace("\\", "/")
                            break
                    
                    if found_path:
                        final_video_path = found_path
                        print(f"✅ 找到匹配的视频文件: {final_video_path}")
                    elif mp4_files:
                        # 使用最新的mp4文件
                        latest_file = max(mp4_files, key=lambda f: os.path.getmtime(os.path.join(self.save_path, f)))
                        final_video_path = os.path.join(self.save_path, latest_file).replace("\\", "/")
                        print(f"✅ 使用最新的MP4文件: {final_video_path}")
                    else:
                        print(f"❌ 未找到任何MP4文件，使用预期路径: {final_video_path}")
                        
                except Exception as e:
                    print(f"搜索视频文件时出错: {e}")
                    
            # 最终验证
            if os.path.exists(final_video_path):
                file_size = os.path.getsize(final_video_path) / (1024 * 1024)  # MB
                print(f"✅ 最终视频文件确认存在: {final_video_path} ({file_size:.2f}MB)")
            else:
                print(f"❌ 警告: 最终视频文件不存在: {final_video_path}")
            
            # --- 步骤 5: 读取转换后的字幕并嵌入到视频 ---
            if not self._is_running: return
            self.progress.emit(80, "处理字幕...")
            
            print(f"查找转换后字幕文件: {converted_subtitle_file}")
            
            # 发送转换后字幕到UI - 使用增强的文件操作
            converted_text = ""
            if converted_subtitle_file:
                try:
                    # 验证文件存在
                    file_info = self.path_manager.get_file_info(converted_subtitle_file)
                    if file_info['exists']:
                        # 使用文件操作助手安全读取
                        converted_text, encoding = self.file_helper.read_subtitle_file(converted_subtitle_file)
                        print(f"✅ 成功读取转换后字幕: {converted_subtitle_file}")
                        print(f"   编码: {encoding}, 大小: {file_info['size_mb']:.2f}MB")
                        self.subtitle_ready.emit(converted_text, "converted")
                    else:
                        raise FileNotFoundError(f"转换后字幕文件不存在: {converted_subtitle_file}")
                        
                except Exception as e:
                    print(f"❌ 读取转换后字幕失败: {e}")
                    print("   使用原始字幕作为备选")
                    converted_text = original_text
                    converted_subtitle_file = subtitle_file
                    self.subtitle_ready.emit(converted_text, "converted")
            else:
                print("⚠️ 警告: 未找到转换后的字幕文件，使用原始字幕")
                converted_text = original_text
                converted_subtitle_file = subtitle_file
                self.subtitle_ready.emit(converted_text, "converted")
            
            # --- 步骤 6: 嵌入字幕到视频 ---
            if not self._is_running: return
            self.progress.emit(90, "嵌入字幕到视频...")
            
            if converted_subtitle_file and os.path.exists(converted_subtitle_file):
                try:
                    print(f"开始嵌入字幕: {converted_subtitle_file} -> {final_video_path}")
                    embed_success = self.embedSubtitles(final_video_path, converted_subtitle_file)
                    if embed_success:
                        print(f"✅ 字幕已成功嵌入到视频: {final_video_path}")
                    else:
                        print(f"⚠️ 字幕嵌入失败，但视频处理成功: {final_video_path}")
                        print("   您可以手动添加字幕文件")
                except Exception as e:
                    print(f"❌ 嵌入字幕时出错: {e}")
                    print("   视频处理成功，但字幕嵌入失败")
            else:
                print(f"⚠️ 跳过字幕嵌入：字幕文件不存在 ({converted_subtitle_file})")
            
            if not self._is_running: return
            self.progress.emit(100, "处理完成！")
            
            # 最终验证输出文件
            if os.path.exists(final_video_path):
                file_size = os.path.getsize(final_video_path) / (1024 * 1024)  # MB
                print(f"✅ 处理完成！最终输出: {final_video_path} ({file_size:.1f}MB)")
                
                # 检查是否有字幕文件可以一起提供
                subtitle_info = ""
                if converted_subtitle_file and os.path.exists(converted_subtitle_file):
                    subtitle_info = f"\n📄 字幕文件: {os.path.basename(converted_subtitle_file)}"
                
                success_message = f"视频处理成功完成！{subtitle_info}"
            else:
                print(f"❌ 警告: 最终输出文件不存在: {final_video_path}")
                success_message = "处理完成，但输出文件验证失败"
            
            # 清理临时文件（可选）
            try:
                # 注意：这里不清理主要的输出文件，只清理真正的临时文件
                # self.path_manager.cleanup_temp_files()
                print("处理完成，保留所有生成的文件")
            except Exception as cleanup_error:
                print(f"清理临时文件时出错: {cleanup_error}")
            
            self.finished.emit(True, final_video_path)  # 传递成功状态和文件路径
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            # 发生错误时也尝试清理临时文件
            try:
                # self.path_manager.cleanup_temp_files()
                print("处理失败，保留文件用于调试")
            except Exception as cleanup_error:
                print(f"错误处理中清理临时文件失败: {cleanup_error}")
            
            self.finished.emit(False, f"处理失败：{str(e)}")
    
    def createTranslatedSubtitle(self, original_subtitle_file, target_lang, conversion_suffix):
        """创建翻译后的字幕文件 - 使用增强的路径管理和错误处理"""
        try:
            # 使用文件操作助手安全读取原始字幕
            original_content, encoding = self.file_helper.read_subtitle_file(original_subtitle_file)
            lines = original_content.splitlines(keepends=True)
            
            # 使用路径管理器创建翻译后的字幕文件路径
            translated_subtitle_file = self.path_manager.get_translated_subtitle_path(conversion_suffix)
            
            print(f"开始创建翻译字幕: {original_subtitle_file} -> {translated_subtitle_file}")
            print(f"目标语言: {target_lang}, 转换后缀: {conversion_suffix}")
            
            # 解析和翻译字幕内容
            translated_lines = []
            i = 0
            translation_count = 0
            
            while i < len(lines):
                # 字幕序号
                if i < len(lines) and lines[i].strip().isdigit():
                    translated_lines.append(lines[i])  # 序号行
                    i += 1
                    
                    # 时间戳行
                    if i < len(lines) and '-->' in lines[i]:
                        translated_lines.append(lines[i])  # 时间戳行
                        i += 1
                        
                        # 字幕文本行（可能有多行）
                        text_lines = []
                        while i < len(lines) and lines[i].strip() and '-->' not in lines[i] and not lines[i].strip().isdigit():
                            text_lines.append(lines[i].strip())
                            i += 1
                        
                        if text_lines:
                            original_text = ' '.join(text_lines)
                            
                            # 翻译文本
                            try:
                                if target_lang == "zh":
                                    translated_text = self.translateToZh(original_text)
                                elif target_lang == "en":
                                    translated_text = self.translateToEn(original_text)
                                else:
                                    translated_text = original_text
                                
                                translated_lines.append(translated_text + '\n')
                                translation_count += 1
                                
                                if translation_count % 10 == 0:
                                    print(f"已翻译 {translation_count} 条字幕...")
                                    
                            except Exception as e:
                                print(f"翻译失败，使用原文: {e}")
                                translated_lines.append(original_text + '\n')
                        
                        # 空行
                        if i < len(lines) and not lines[i].strip():
                            translated_lines.append(lines[i])
                            i += 1
                    else:
                        i += 1
                else:
                    # 跳过无效行
                    if i < len(lines):
                        translated_lines.append(lines[i])
                    i += 1
            
            # 使用文件操作助手安全写入翻译后的字幕文件
            translated_content = ''.join(translated_lines)
            success = self.file_helper.write_subtitle_file(translated_subtitle_file, translated_content, 'utf-8')
            
            if success:
                # 验证生成的文件
                file_info = self.path_manager.get_file_info(translated_subtitle_file)
                if file_info['exists']:
                    print(f"✅ 翻译字幕文件已生成: {translated_subtitle_file}")
                    print(f"   文件大小: {file_info['size_mb']:.2f}MB, 翻译条数: {translation_count}")
                    return translated_subtitle_file
                else:
                    raise Exception("翻译字幕文件生成后验证失败")
            else:
                raise Exception("翻译字幕文件写入失败")
            
        except Exception as e:
            print(f"❌ 生成翻译字幕失败: {e}")
            print(f"   返回原始字幕文件: {original_subtitle_file}")
            return original_subtitle_file
    
    def translateToZh(self, text):
        """翻译为中文"""
        try:
            import Baidu_Text_transAPI
            result = Baidu_Text_transAPI.translate(text, 'en', 'zh')
            return result if result else text
        except Exception as e:
            print(f"翻译失败: {e}")
            return text
    
    def translateToEn(self, text):
        """翻译为英文"""
        try:
            import Baidu_Text_transAPI
            result = Baidu_Text_transAPI.translate(text, 'zh', 'en')
            return result if result else text
        except Exception as e:
            print(f"翻译失败: {e}")
            return text

    def embedSubtitles(self, video_file, subtitle_file):
        """将字幕嵌入到视频中 - 改进版"""
        if not os.path.exists(subtitle_file):
            print(f"字幕文件不存在: {subtitle_file}")
            return False
        
        if not os.path.exists(video_file):
            print(f"视频文件不存在: {video_file}")
            return False
        
        print(f"开始嵌入字幕: {subtitle_file} -> {video_file}")
        
        try:
            import subprocess
            import shutil
            
            # 检查ffmpeg是否可用
            try:
                result = subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True, text=True, encoding='utf-8', errors='replace')
                print("FFmpeg 可用")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("警告: ffmpeg不可用，跳过字幕嵌入")
                return False
            
            # 标准化路径
            video_file = os.path.abspath(video_file).replace('\\', '/')
            subtitle_file = os.path.abspath(subtitle_file).replace('\\', '/')
            
            # 创建带字幕的新视频文件名
            base_name, ext = os.path.splitext(video_file)
            output_with_subs = f"{base_name}_with_subtitles{ext}"
            
            print(f"输入视频: {video_file}")
            print(f"字幕文件: {subtitle_file}")
            print(f"输出视频: {output_with_subs}")
            
            # 验证字幕文件格式
            try:
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    subtitle_content = f.read()
                    if not subtitle_content.strip():
                        print("字幕文件为空")
                        return False
                    print(f"字幕文件验证通过，内容长度: {len(subtitle_content)} 字符")
            except Exception as e:
                print(f"字幕文件验证失败: {e}")
                return False
            
            # 方法1: 使用subtitles滤镜（推荐）
            cmd1 = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-vf', f"subtitles='{subtitle_file}':force_style='FontName=Arial,FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,BorderStyle=1,Outline=2,Shadow=1'",
                '-c:a', 'copy',
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                output_with_subs
            ]
            
            # 方法2: 简化版本（备用）
            cmd2 = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-vf', f"subtitles='{subtitle_file}'",
                '-c:a', 'copy',
                output_with_subs
            ]
            
            # 方法3: 使用ass滤镜（最后备用）
            cmd3 = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-vf', f"ass='{subtitle_file}'",
                '-c:a', 'copy',
                output_with_subs
            ]
            
            success = False
            
            # 尝试方法1
            print("尝试方法1: 高级字幕嵌入...")
            try:
                result = subprocess.run(cmd1, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
                if result.returncode == 0 and os.path.exists(output_with_subs):
                    print("方法1成功")
                    success = True
                else:
                    print(f"方法1失败: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("方法1超时")
            except Exception as e:
                print(f"方法1异常: {e}")
            
            # 如果方法1失败，尝试方法2
            if not success:
                print("尝试方法2: 简化字幕嵌入...")
                try:
                    result = subprocess.run(cmd2, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
                    if result.returncode == 0 and os.path.exists(output_with_subs):
                        print("方法2成功")
                        success = True
                    else:
                        print(f"方法2失败: {result.stderr}")
                except subprocess.TimeoutExpired:
                    print("方法2超时")
                except Exception as e:
                    print(f"方法2异常: {e}")
            
            # 如果方法2也失败，尝试转换字幕格式后再试
            if not success:
                print("尝试转换字幕格式...")
                try:
                    # 创建ASS格式字幕文件
                    ass_file = subtitle_file.replace('.srt', '.ass')
                    self.convertSrtToAss(subtitle_file, ass_file)
                    
                    if os.path.exists(ass_file):
                        cmd3_ass = [
                            'ffmpeg', '-y',
                            '-i', video_file,
                            '-vf', f"ass='{ass_file}'",
                            '-c:a', 'copy',
                            output_with_subs
                        ]
                        
                        result = subprocess.run(cmd3_ass, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
                        if result.returncode == 0 and os.path.exists(output_with_subs):
                            print("ASS格式字幕嵌入成功")
                            success = True
                        else:
                            print(f"ASS格式嵌入失败: {result.stderr}")
                except Exception as e:
                    print(f"ASS格式转换失败: {e}")
            
            if success and os.path.exists(output_with_subs):
                # 验证输出文件
                output_size = os.path.getsize(output_with_subs)
                if output_size > 0:
                    # 备份原文件
                    backup_file = f"{base_name}_original{ext}"
                    if not os.path.exists(backup_file):
                        shutil.copy2(video_file, backup_file)
                        print(f"原文件已备份为: {backup_file}")
                    
                    # 替换为带字幕的版本
                    shutil.move(output_with_subs, video_file)
                    print(f"✅ 字幕已成功嵌入到视频: {video_file}")
                    print(f"   输出文件大小: {output_size / (1024*1024):.1f} MB")
                    return True
                else:
                    print("输出文件大小为0，嵌入失败")
                    if os.path.exists(output_with_subs):
                        os.remove(output_with_subs)
                    return False
            else:
                print("❌ 所有字幕嵌入方法都失败了")
                return False
                
        except subprocess.TimeoutExpired:
            print("字幕嵌入超时（5分钟），跳过此步骤")
            return False
        except Exception as e:
            print(f"嵌入字幕失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def convertSrtToAss(self, srt_file, ass_file):
        """将SRT字幕转换为ASS格式"""
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # ASS文件头
            ass_header = """[Script Info]
Title: Converted Subtitle
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&Hffffff,&Hffffff,&H0,&H0,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            
            # 解析SRT并转换为ASS
            lines = srt_content.strip().split('\n')
            ass_events = []
            
            i = 0
            while i < len(lines):
                if lines[i].strip().isdigit():
                    # 序号行
                    i += 1
                    if i < len(lines) and '-->' in lines[i]:
                        # 时间行
                        time_line = lines[i].strip()
                        start_time, end_time = time_line.split(' --> ')
                        
                        # 转换时间格式 (SRT: 00:00:00,000 -> ASS: 0:00:00.00)
                        start_ass = start_time.replace(',', '.')[:-1]  # 去掉最后一位毫秒
                        end_ass = end_time.replace(',', '.')[:-1]
                        
                        i += 1
                        # 文本行
                        text_lines = []
                        while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                            text_lines.append(lines[i].strip())
                            i += 1
                        
                        if text_lines:
                            text = '\\N'.join(text_lines)  # ASS使用\N作为换行符
                            ass_events.append(f"Dialogue: 0,{start_ass},{end_ass},Default,,0,0,0,,{text}")
                else:
                    i += 1
            
            # 写入ASS文件
            with open(ass_file, 'w', encoding='utf-8') as f:
                f.write(ass_header)
                f.write('\n'.join(ass_events))
            
            print(f"SRT转ASS完成: {ass_file}")
            return True
            
        except Exception as e:
            print(f"SRT转ASS失败: {e}")
            return False

    def stop(self):
        # NEW: 优雅地停止线程
        self._is_running = False

class EnhancedMainWindow(QMainWindow):
    """增强版主窗口 v3.1"""
    def __init__(self):
        super().__init__()
        self.video_path = ""
        self.output_path = ""
        self.process_thread = None
        
        # 初始化缩放管理器
        self.zoom_manager = ZoomManager(self)
        self.zoom_manager.zoomChanged.connect(self.applyZoom)
        
        self.setupUi()
        self.loadSavedTheme()
        
        # 添加缩放快捷键
        self.setupZoomShortcuts()
        
    def setupUi(self):
        self.setWindowTitle("智能多语言视频语音转换系统 v3.1")
        # 使用自定义应用程序图标
        try:
            custom_icon = app_icon.create_app_icon()
            self.setWindowIcon(custom_icon)
        except:
            # 备用方案：使用系统图标
            self.setWindowIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        # 减小最小窗口大小，更适合小屏幕
        self.setMinimumSize(800, 600)  # 从900x650调整为800x600
        self.resize(950, 650)  # 从1000x700调整为950x650，更紧凑
        
        # 窗口居中显示
        self.centerWindow()
        
        # 中央组件与主布局 - 改为垂直布局，标题在顶部居中
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 优化边距和间距
        main_layout.setContentsMargins(12, 12, 12, 12)  # 减小边距
        main_layout.setSpacing(10)  # 减小间距

        # 标题区域 - 居中显示
        title_section = self.createTitleSection()
        main_layout.addLayout(title_section)
        
        # 内容区域 - 水平布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)  # 减小间距
        
        # 左侧控制区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)  # 统一间距
        left_layout.setContentsMargins(8, 8, 8, 8)  # 适当的边距
        left_layout.addWidget(self.createFileSection())
        left_layout.addWidget(self.createConversionSection())
        left_layout.addWidget(self.createProgressSection())
        left_layout.addWidget(self.createButtonSection())
        left_layout.addWidget(self.createResultSection())
        left_layout.addStretch()
        
        # 右侧字幕显示区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(self.createSubtitleSection())
        
        # 设置左右区域比例
        content_layout.addWidget(left_widget, 1)  # 左侧占1/3
        content_layout.addWidget(right_widget, 2)  # 右侧占2/3
        
        main_layout.addLayout(content_layout, 1)  # 内容区域占主要空间
        
        self.createMenuBar()
        self.createStatusBar()
    
    def centerWindow(self):
        """将窗口居中显示在屏幕上，支持动态居中"""
        try:
            # 获取屏幕几何信息
            screen = QApplication.desktop().screenGeometry()
            # 获取窗口几何信息
            window = self.frameGeometry()
            
            # 计算居中位置
            center_x = (screen.width() - window.width()) // 2
            center_y = (screen.height() - window.height()) // 2
            
            # 确保窗口不会超出屏幕边界
            center_x = max(0, center_x)
            center_y = max(0, center_y)
            
            # 移动窗口到居中位置
            self.move(center_x, center_y)
            
        except Exception as e:
            print(f"居中窗口失败: {e}")
            # 备用方案：使用Qt的居中方法
            try:
                screen_geometry = QApplication.desktop().screenGeometry()
                window_geometry = self.frameGeometry()
                center_point = screen_geometry.center()
                window_geometry.moveCenter(center_point)
                self.move(window_geometry.topLeft())
            except Exception as e2:
                print(f"备用居中方法也失败: {e2}")
    
    def ensureWindowVisible(self):
        """确保窗口在屏幕可见范围内"""
        try:
            screen = QApplication.desktop().screenGeometry()
            window = self.frameGeometry()
            
            # 调整X坐标
            if window.right() > screen.right():
                self.move(screen.right() - window.width(), window.y())
            elif window.left() < screen.left():
                self.move(screen.left(), window.y())
            
            # 调整Y坐标
            if window.bottom() > screen.bottom():
                self.move(window.x(), screen.bottom() - window.height())
            elif window.top() < screen.top():
                self.move(window.x(), screen.top())
                
        except Exception as e:
            print(f"调整窗口位置失败: {e}")
    
    def setupZoomShortcuts(self):
        """设置缩放快捷键"""
        # Ctrl+Plus 放大 - 使用不同的快捷键避免冲突
        zoom_in_shortcut = QShortcut(QKeySequence("Ctrl+Shift+="), self)
        zoom_in_shortcut.activated.connect(self.zoom_manager.zoomIn)
        
        # Ctrl+Minus 缩小 - 使用不同的快捷键避免冲突
        zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+Shift+-"), self)
        zoom_out_shortcut.activated.connect(self.zoom_manager.zoomOut)
        
        # Ctrl+0 重置缩放
        zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+Shift+0"), self)
        zoom_reset_shortcut.activated.connect(self.zoom_manager.resetZoom)
    
    def applyZoom(self, factor):
        """应用整体UI缩放 - 优化版本，保持风格一致性"""
        try:
            print(f"开始应用优化缩放: {factor}")
            
            # 1. 计算缩放后的窗口大小 - 基于标准尺寸
            base_width = 950
            base_height = 650
            new_width = int(base_width * factor)
            new_height = int(base_height * factor)
            
            # 2. 获取屏幕大小，确保窗口不超出屏幕
            screen = QApplication.desktop().screenGeometry()
            max_width = int(screen.width() * 0.9)  # 留出边距
            max_height = int(screen.height() * 0.9)
            
            # 3. 限制窗口大小在合理范围内
            new_width = min(new_width, max_width)
            new_height = min(new_height, max_height)
            
            # 确保最小尺寸
            min_width = 700  # 固定最小宽度
            min_height = 500  # 固定最小高度
            new_width = max(new_width, min_width)
            new_height = max(new_height, min_height)
            
            # 4. 调整窗口大小
            current_size = self.size()
            if abs(current_size.width() - new_width) > 10 or abs(current_size.height() - new_height) > 10:
                self.resize(new_width, new_height)
                print(f"窗口大小调整为: {new_width}x{new_height}")
            
            # 5. 重新居中窗口
            self.centerWindow()
            
            # 6. 应用保持原有风格的缩放样式
            self.applyStyleZoom(factor)
            
            # 7. 调整特定组件的尺寸
            self.adjustComponentSizes(factor)
            
            # 8. 强制更新界面
            self.update()
            QApplication.processEvents()
            
            print(f"优化缩放完成: {factor}, 窗口: {new_width}x{new_height}")
            
        except Exception as e:
            print(f"缩放失败: {e}")
            import traceback
            traceback.print_exc()
    
    def adjustComponentSizes(self, factor):
        """调整特定组件的尺寸以适应缩放"""
        try:
            # 调整结果区域的高度
            if hasattr(self, 'result_group'):
                base_height = 200
                new_height = max(180, min(300, int(base_height * factor)))
                self.result_group.setMinimumHeight(new_height)
                self.result_group.setMaximumHeight(new_height + 60)
            
            # 调整配置转换区域
            if hasattr(self, 'conversion_group'):
                base_height = 200
                new_height = max(180, min(280, int(base_height * factor)))
                self.conversion_group.setMinimumHeight(new_height)
                self.conversion_group.setMaximumHeight(new_height + 40)
            
            # 调整滚动区域
            if hasattr(self, 'result_scroll_area'):
                base_height = 120
                new_height = max(100, min(200, int(base_height * factor)))
                self.result_scroll_area.setMinimumHeight(new_height)
                self.result_scroll_area.setMaximumHeight(new_height + 80)
            
            # 调整按钮大小
            buttons = self.findChildren(QPushButton)
            for button in buttons:
                if button.objectName() == "processButton":
                    base_height = 40
                    new_height = max(30, min(50, int(base_height * factor)))
                    button.setMinimumHeight(new_height)
                else:
                    base_height = 32
                    new_height = max(25, min(40, int(base_height * factor)))
                    button.setMinimumHeight(new_height)
            
            # 调整组合框大小
            combos = self.findChildren(QComboBox)
            for combo in combos:
                base_height = 28
                new_height = max(24, min(35, int(base_height * factor)))
                combo.setMinimumHeight(new_height)
            
            print(f"组件尺寸调整完成: 缩放因子 {factor}")
            
        except Exception as e:
            print(f"组件尺寸调整失败: {e}")
    
    def applyStyleZoom(self, factor):
        """应用样式缩放，保持原有UI风格，只调整尺寸"""
        try:
            # 1. 读取原始样式文件，保持原有风格
            original_style = ""
            theme = 'light'
            
            # 获取当前主题设置
            if os.path.exists('config.json'):
                try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        theme = config.get('theme', 'light')
                except:
                    pass
            
            # 读取对应的样式文件
            style_file = "style_dark.qss" if theme == 'dark' else "style.qss"
            
            if os.path.exists(style_file):
                try:
                    with open(style_file, "r", encoding="utf-8") as f:
                        original_style = f.read()
                    print(f"成功读取样式文件: {style_file}")
                except Exception as e:
                    print(f"读取样式文件失败: {e}")
                    original_style = ""
            else:
                print(f"样式文件不存在: {style_file}")
            
            # 2. 计算缩放参数
            base_font_size = 9
            scaled_font_size = max(8, int(base_font_size * factor))
            
            # 只添加尺寸缩放的样式，不改变原有的颜色和风格
            zoom_adjustments = f"""
            /* === 缩放尺寸调整 === */
        QWidget {{
                font-size: {scaled_font_size}px;
        }}
        
        /* 标题缩放 */
        #titleLabel {{
            font-size: {max(16, int(22 * factor))}px;
        }}
        
        #subtitleLabel {{
            font-size: {max(10, int(14 * factor))}px;
        }}
        
            /* 按钮尺寸缩放 */
        QPushButton {{
            min-height: {max(20, int(30 * factor))}px;
            padding: {max(4, int(8 * factor))}px {max(6, int(12 * factor))}px;
            font-size: {max(8, int(10 * factor))}px;
        }}
        
        #processButton {{
            min-height: {max(25, int(40 * factor))}px;
                font-size: {max(9, int(12 * factor))}px;
        }}
        
            /* 组合框尺寸缩放 */
        QComboBox {{
                min-height: {max(18, int(26 * factor))}px;
                padding: {max(3, int(6 * factor))}px {max(4, int(8 * factor))}px;
                font-size: {scaled_font_size}px;
            }}
            
            QLineEdit {{
            padding: {max(4, int(8 * factor))}px;
                font-size: {scaled_font_size}px;
        }}
        
            /* 分组框尺寸缩放 */
        QGroupBox {{
            font-size: {max(9, int(11 * factor))}px;
                padding-top: {max(8, int(15 * factor))}px;
                margin-top: {max(6, int(10 * factor))}px;
        }}
        
            QGroupBox::title {{
                padding: 0 {max(3, int(5 * factor))}px 0 {max(3, int(5 * factor))}px;
        }}
        
            /* 文本区域尺寸缩放 */
        QTextEdit {{
                font-size: {scaled_font_size}px;
                padding: {max(6, int(10 * factor))}px;
            }}
            
            QLabel {{
                font-size: {scaled_font_size}px;
            }}
            
            /* 进度条尺寸缩放 */
        QProgressBar {{
                height: {max(6, int(10 * factor))}px;
            margin: {max(4, int(8 * factor))}px 0;
        }}
        
            /* 滚动条尺寸缩放 */
            QScrollBar:vertical {{
                width: {max(8, int(12 * factor))}px;
            }}
            
            QScrollBar::handle:vertical {{
                min-height: {max(10, int(20 * factor))}px;
            }}
            
            /* 标签页尺寸缩放 */
            QTabBar::tab {{
                padding: {max(4, int(8 * factor))}px {max(6, int(12 * factor))}px;
                font-size: {scaled_font_size}px;
            }}
            
            /* 特殊区域尺寸缩放 */
        #dropAreaLabel {{
            padding: {max(15, int(25 * factor))}px;
                font-size: {max(9, int(12 * factor))}px;
            }}
            
            #statusLabel {{
                font-size: {scaled_font_size}px;
                padding: {max(3, int(6 * factor))}px;
            }}
            
            #resultLabel {{
                font-size: {max(10, int(12 * factor))}px;
            }}
            """
            
            # 3. 组合原始样式和缩放调整
            if original_style:
                # 如果有原始样式，将缩放调整附加到原样式后面
                combined_style = original_style + "\n" + zoom_adjustments
            else:
                # 如果没有原始样式，只使用缩放调整
                combined_style = zoom_adjustments
            
            # 4. 应用组合后的样式
            self.setStyleSheet(combined_style)
            
            # 5. 强制更新界面
            self.update()
            QApplication.processEvents()
            
            print(f"缩放样式应用成功: {factor}, 字体: {scaled_font_size}px, 保持原有风格")
            
        except Exception as e:
            print(f"样式缩放失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 备用方案：只调整字体大小
            try:
                font = QApplication.font()
                font.setPointSize(max(8, int(9 * factor)))
                QApplication.setFont(font)
                print("使用备用字体缩放方案")
            except Exception as font_error:
                print(f"备用方案也失败: {font_error}")

    def createTitleSection(self):
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # 左边留空，实现居中
        layout.addStretch()
        
        # 中央标题区域
        title_container = QVBoxLayout()
        title_container.setSpacing(8)
        
        # 主标题容器（图标+文字）
        title_row = QHBoxLayout()
        title_row.setSpacing(12)
        
        # 应用图标 - 使用媒体播放图标体现视频处理主题
        app_icon = QLabel()
        app_icon.setPixmap(self.style().standardIcon(QStyle.SP_MediaPlay).pixmap(48, 48))
        app_icon.setAlignment(Qt.AlignCenter)
        
        # 主标题
        title_label = QLabel("智能视频语音转换系统")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        
        title_row.addWidget(app_icon)
        title_row.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel("AI-Powered Video Voice Dubbing")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        title_container.addLayout(title_row)
        title_container.addWidget(subtitle_label)
        
        layout.addLayout(title_container)
        
        # 右边留空，实现居中
        layout.addStretch()
        
        return layout

    def createFileSection(self):
        group = QGroupBox("1. 选择文件")
        group.setObjectName("fileSection")
        layout = QVBoxLayout(group)
        
        # 输入文件（使用自定义组件）
        self.file_input_widget = FileInputWidget()
        self.file_input_widget.pathChanged.connect(self.on_video_path_changed)
        
        # 输出目录 - 简化图标，只保留必要的
        output_layout = QHBoxLayout()
        
        output_label = QLabel("输出到:")
        output_label.setObjectName("outputLabel")
        
        self.output_path_label = QLabel("<i>尚未选择输出目录</i>")
        self.output_path_label.setObjectName("pathLabel")
        self.output_path_label.setStyleSheet("font-style: italic; color: #6c757d;")
        
        output_btn = QPushButton("浏览")
        output_btn.setIcon(self.style().standardIcon(QStyle.SP_DriveHDIcon))  # 存储设备图标
        output_btn.clicked.connect(self.selectOutputDir)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path_label, 1)
        output_layout.addWidget(output_btn)
        
        layout.addWidget(self.file_input_widget)
        layout.addLayout(output_layout)
        return group

    def createConversionSection(self):
        group = QGroupBox("2. 配置转换")
        group.setObjectName("conversionSection")
        self.conversion_group = group  # 保存引用供缩放使用
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建网格布局，更合理地安排组件
        main_form = QGridLayout()
        main_form.setSpacing(12)
        main_form.setVerticalSpacing(12)
        main_form.setContentsMargins(0, 0, 0, 0)
        
        # 统一的标签样式 - 调整字体大小与其他部分一致
        label_style = """
            QLabel {
                color: #333; 
                font-size: 13px; 
                min-width: 70px;
                background: transparent;
                border: none;
                padding: 0px;
            }
        """
        
        # 第一行：转换类型和发音人
        conversion_label = QLabel("转换类型:")
        conversion_label.setStyleSheet(label_style)
        self.conversion_combo = QComboBox()
        # 移除自定义样式，使用原生外观
        self.conversion_combo.addItems([
            "智能转换",
            "中文转英文",
            "中文转中文",  
            "英文转中文",
            "英文转英文"
        ])
        
        voice_label = QLabel("发音人:")
        voice_label.setStyleSheet(label_style)
        self.voice_combo = QComboBox()
        # 移除自定义样式，使用原生外观
        voice_items = [
            "xiaoyan - 小燕（女声）",
            "xiaoyu - 小宇（男声）", 
            "xiaoxin - 小欣（女声）",
            "aisxping - 小萍（女声）",
            "x4_EnUs_Laura_education - Laura（英文女声）",
            "x4_EnUs_Emma_education - Emma（英文女声）",
            "x4_EnUs_Alex_education - Alex（英文男声）"
        ]
        self.voice_combo.addItems(voice_items)
        
        # 第二行：语速和音量（使用EnhancedSlider，保持在同一行）
        speed_label = QLabel("语速:")
        speed_label.setStyleSheet(label_style)
        self.speed_slider = EnhancedSlider(50, 200, 100, 5, "%")
        self.speed_slider.setFixedWidth(220)  # 增加滑动条宽度
        
        volume_label = QLabel("音量:")
        volume_label.setStyleSheet(label_style)
        self.volume_slider = EnhancedSlider(0, 100, 80, 5, "%")
        self.volume_slider.setFixedWidth(220)  # 增加滑动条宽度，与语速保持一致
        
        # 第二行：输出质量（和语速、音量在同一行，但在右侧）
        quality_label = QLabel("输出质量:")
        quality_label.setStyleSheet(label_style)
        self.quality_combo = QComboBox()
        # 移除自定义样式，使用原生外观
        quality_items = ["标准质量", "高质量", "超清质量"]
        self.quality_combo.addItems(quality_items)
        self.quality_combo.setCurrentIndex(1)  # 默认高质量
        
        # 布局安排 - 2行4列布局
        # 第一行：转换类型 | 转换类型控件 | 发音人 | 发音人控件
        main_form.addWidget(conversion_label, 0, 0)
        main_form.addWidget(self.conversion_combo, 0, 1)
        main_form.addWidget(voice_label, 0, 2)
        main_form.addWidget(self.voice_combo, 0, 3)
        
        # 第二行：语速 | 语速控件 | 音量 | 音量控件
        main_form.addWidget(speed_label, 1, 0)
        main_form.addWidget(self.speed_slider, 1, 1)
        main_form.addWidget(volume_label, 1, 2)
        main_form.addWidget(self.volume_slider, 1, 3)
        
        # 第三行：输出质量 | 质量控件 | （空） | （空）
        main_form.addWidget(quality_label, 2, 0)
        main_form.addWidget(self.quality_combo, 2, 1)
        
        # 设置列伸缩 - 让组件有合适的空间
        main_form.setColumnStretch(0, 0)  # 标签列固定宽度
        main_form.setColumnStretch(1, 1)  # 控件列可伸缩
        main_form.setColumnStretch(2, 0)  # 标签列固定宽度
        main_form.setColumnStretch(3, 1)  # 控件列可伸缩
        
        # 添加到主布局
        layout.addLayout(main_form)
        layout.addStretch()  # 添加弹性空间，防止组件过度拉伸
        
        return group

    def createProgressSection(self):
        group = QGroupBox("3. 查看进度")
        group.setObjectName("progressSection")
        layout = QVBoxLayout(group)
        
        # 进度条 - 不需要额外图标
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        
        # 状态显示 - 不需要额外图标
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("statusLabel")
        
        layout.addWidget(QLabel("进度:"))
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        return group

    def createButtonSection(self):
        """创建按钮区域 - 精简图标，只保留核心功能图标"""
        group = QGroupBox("4. 操作控制")
        group.setObjectName("buttonSection")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # 主操作按钮 - 保留播放图标
        self.process_btn = QPushButton("开始转换")
        self.process_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.process_btn.setObjectName("processButton")
        self.process_btn.setFixedHeight(40)
        self.process_btn.setMinimumWidth(120)
        self.process_btn.clicked.connect(self.startProcessing)
        
        # 停止按钮 - 保留停止图标
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setFixedHeight(35)
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stopProcessing)
        
        # 其他按钮 - 移除图标，保持简洁
        self.preview_btn = QPushButton("预览")
        self.preview_btn.setObjectName("previewButton")
        self.preview_btn.setFixedHeight(35)
        self.preview_btn.setFixedWidth(80)
        self.preview_btn.clicked.connect(self.openPreview)
        
        self.settings_btn = QPushButton("设置")
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.setFixedHeight(35)
        self.settings_btn.setFixedWidth(80)
        self.settings_btn.clicked.connect(self.openSettings)
        
        self.batch_btn = QPushButton("批量")
        self.batch_btn.setObjectName("batchButton")
        self.batch_btn.setFixedHeight(35)
        self.batch_btn.setFixedWidth(80)
        self.batch_btn.clicked.connect(self.openBatchProcessor)
        
        layout.addStretch()
        layout.addWidget(self.process_btn)
        layout.addSpacing(10)
        layout.addWidget(self.stop_btn)
        layout.addSpacing(20)
        layout.addWidget(self.preview_btn)
        layout.addWidget(self.settings_btn)
        layout.addWidget(self.batch_btn)
        layout.addStretch()
        
        return group

    def createResultSection(self):
        """创建结果显示区域 - 重新设计，确保可以完整滚动显示"""
        group = QGroupBox("5. 处理结果")
        group.setObjectName("resultSection")
        self.result_group = group  # 保存引用供缩放使用
        group.setMinimumHeight(200)  # 减小最小高度
        group.setMaximumHeight(250)  # 减小最大高度，为其他区域留出空间
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 结果显示滚动区域 - 重新调整高度
        self.result_scroll_area = QScrollArea()
        self.result_scroll_area.setWidgetResizable(True)
        self.result_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.result_scroll_area.setMinimumHeight(110)  # 减小最小可视高度
        self.result_scroll_area.setMaximumHeight(150)  # 减小最大高度
        self.result_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #fafafa;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        # 结果内容容器
        result_content_widget = QWidget()
        result_content_layout = QVBoxLayout(result_content_widget)
        result_content_layout.setContentsMargins(8, 8, 8, 8)
        result_content_layout.setSpacing(5)
        
        # 结果文本标签
        self.result_label = QLabel(self.getInitialResultText())
        self.result_label.setWordWrap(True)  # 允许文字换行
        self.result_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 顶部左对齐
        self.result_label.setObjectName("resultLabel")
        self.result_label.setStyleSheet("""
            QLabel#resultLabel {
                padding: 12px;
                border: none;
                border-radius: 6px;
                background-color: #f8f9fa;
                color: #666;
                font-size: 12px;
                line-height: 1.5;
                min-height: 60px;
            }
        """)
        
        # 设置文本可选择（方便复制）
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        result_content_layout.addWidget(self.result_label)
        result_content_layout.addStretch()  # 添加弹性空间
        
        # 设置滚动区域的内容
        self.result_scroll_area.setWidget(result_content_widget)
        
        # 按钮区域 - 固定在底部，减小高度
        button_container = QWidget()
        button_container.setFixedHeight(42)  # 减小按钮区域高度
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(5, 6, 5, 6)
        
        # 打开文件夹按钮
        self.open_result_btn = QPushButton("打开文件夹")
        self.open_result_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.open_result_btn.setToolTip("打开输出文件夹")
        self.open_result_btn.setFixedHeight(30)  # 减小按钮高度
        self.open_result_btn.setMinimumWidth(100)
        self.open_result_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                border: 1px solid #0078D7;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 10px;
                background-color: white;
                color: #0078D7;
            }
            QPushButton:hover {
                background-color: #0078D7;
                color: white;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
                border-color: #ddd;
            }
        """)
        
        # 播放视频按钮
        self.play_result_btn = QPushButton("播放视频")
        self.play_result_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_result_btn.setToolTip("播放处理后的视频")
        self.play_result_btn.setFixedHeight(30)  # 减小按钮高度
        self.play_result_btn.setMinimumWidth(100)
        self.play_result_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                border: 1px solid #28a745;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 10px;
                background-color: white;
                color: #28a745;
            }
            QPushButton:hover {
                background-color: #28a745;
                color: white;
            }
            QPushButton:disabled {
                background-color: #f0f0f0;
                color: #999;
                border-color: #ddd;
            }
        """)
        
        # 初始状态禁用按钮
        self.open_result_btn.setEnabled(False)
        self.play_result_btn.setEnabled(False)
        
        # 连接按钮事件
        self.open_result_btn.clicked.connect(self.openResultFolder)
        self.play_result_btn.clicked.connect(self.playResultVideo)
        
        # 按钮布局
        button_layout.addWidget(self.open_result_btn)
        button_layout.addWidget(self.play_result_btn)
        button_layout.addStretch()  # 右侧弹性空间
        
        # 组装主布局
        layout.addWidget(self.result_scroll_area, 1)  # 滚动区域占主要空间
        layout.addWidget(button_container, 0)  # 按钮区域固定大小
        
        return group
    
    def getInitialResultText(self):
        """获取初始的结果显示文字"""
        if not self.video_path:
            return "📋 请先选择视频文件 ➤ 配置转换参数 ➤ 开始处理"
        else:
            file_name = os.path.basename(self.video_path)
            return f"✅ 已选择文件: {file_name}\n\n📋 配置转换参数后即可开始处理 ➤➤➤"
    
    def updateResultDisplay(self, text, style_type="info"):
        """更新结果显示，支持动态高度适配"""
        try:
            # 检查是否是成功状态且有视频文件
            if style_type == "success" and hasattr(self, 'last_output_path') and self.last_output_path:
                # 创建带可点击链接的文本
                file_name = os.path.basename(self.last_output_path)
                dir_name = os.path.dirname(self.last_output_path)
                try:
                    file_size = os.path.getsize(self.last_output_path) / (1024 * 1024)
                    size_text = f"{file_size:.1f} MB"
                except:
                    size_text = "未知大小"
                
                # 使用 HTML 格式，添加可点击的链接
                html_text = f"""
                <div style="text-align: center;">
                    <h3 style="color: #28a745; margin-bottom: 15px;">✅ 处理成功完成！</h3>
                    
                    <p style="margin: 8px 0;"><strong>📁 输出文件:</strong> {file_name}</p>
                    <p style="margin: 8px 0;"><strong>📂 保存目录:</strong> {dir_name}</p>
                    <p style="margin: 8px 0;"><strong>📏 文件大小:</strong> {size_text}</p>
                    
                    <p style="margin: 15px 0 8px 0;">您可以点击下方按钮打开文件夹，或者</p>
                    <p style="margin: 0;">
                        <a href="play_video" style="color: #0078D7; text-decoration: none; font-weight: bold; font-size: 14px; 
                           padding: 8px 16px; border: 2px solid #0078D7; border-radius: 6px; background: linear-gradient(135deg, #f8f9ff 0%, #e6f2ff 100%);
                           display: inline-block; transition: all 0.3s ease;">
                            🎬 点此播放视频
                        </a>
                    </p>
                </div>
                """
                
                self.result_label.setText(html_text)
                self.result_label.setTextFormat(Qt.RichText)
                self.result_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
                self.result_label.linkActivated.connect(self.onResultLinkClicked)
                
                # 成功样式 - 适配富文本
                style = """
                    QLabel#resultLabel {
                        padding: 15px;
                        border: 2px solid #28a745;
                        border-radius: 8px;
                        background-color: #d4edda;
                        color: #155724;
                        font-size: 12px;
                        line-height: 1.4;
                        min-height: 120px;
                    }
                    QLabel#resultLabel a:hover {
                        background-color: #0078D7 !important;
                        color: white !important;
                        transform: translateY(-1px);
                        box-shadow: 0 4px 8px rgba(0, 120, 215, 0.3);
                    }
                """
            else:
                # 普通文本处理
                self.result_label.setText(text)
                self.result_label.setTextFormat(Qt.PlainText)
                self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                
                # 根据文本长度动态调整显示样式
                text_length = len(text)
                
                if style_type == "success":
                    # 成功样式
                    style = """
                        QLabel#resultLabel {
                            padding: 12px;
                            border: 2px solid #28a745;
                            border-radius: 8px;
                            background-color: #d4edda;
                            color: #155724;
                            font-size: 12px;
                            line-height: 1.4;
                            min-height: 80px;
                        }
                    """
                elif style_type == "error":
                    # 错误样式
                    style = """
                        QLabel#resultLabel {
                            padding: 12px;
                            border: 2px solid #dc3545;
                            border-radius: 8px;
                            background-color: #f8d7da;
                            color: #721c24;
                            font-size: 12px;
                            line-height: 1.4;
                            min-height: 80px;
                        }
                    """
                elif style_type == "processing":
                    # 处理中样式
                    style = """
                        QLabel#resultLabel {
                            padding: 12px;
                            border: 2px solid #0078D7;
                            border-radius: 8px;
                            background-color: #cce7ff;
                            color: #004085;
                            font-size: 12px;
                            line-height: 1.4;
                            min-height: 60px;
                        }
                    """
                else:
                    # 默认信息样式
                    style = """
                        QLabel#resultLabel {
                            padding: 15px;
                            border: 2px solid #ddd;
                            border-radius: 8px;
                            background-color: #f8f9fa;
                            color: #666;
                            font-size: 13px;
                            line-height: 1.5;
                            min-height: 60px;
                        }
                    """
                
                # 如果文本很长，确保滚动区域可以正确显示
                if text_length > 200:
                    self.result_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                else:
                    self.result_label.setAlignment(Qt.AlignCenter)
            
            self.result_label.setStyleSheet(style)
                
        except Exception as e:
            print(f"更新结果显示失败: {e}")
    
    def onResultLinkClicked(self, link):
        """处理结果区域的链接点击"""
        if link == "play_video":
            self.playResultVideo()
    
    def createSubtitleSection(self):
        """创建字幕显示区域 - 精简图标使用"""
        group = QGroupBox("字幕预览与编辑")
        group.setObjectName("subtitleSection")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # 字幕统计信息栏 - 移除图标
        self.subtitle_stats = QLabel("统计: 等待处理...")
        self.subtitle_stats.setObjectName("subtitleStats")
        self.subtitle_stats.setStyleSheet("""
            QLabel#subtitleStats {
                color: #0078D7; 
                font-size: 12px; 
                font-weight: 600;
                padding: 4px 8px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 120, 215, 0.1), stop:1 rgba(0, 120, 215, 0.05));
                border-radius: 4px;
                border: 1px solid rgba(0, 120, 215, 0.2);
            }
        """)
        
        # 字幕标签页 - 不使用图标
        self.subtitle_tabs = QTabWidget()
        self.subtitle_tabs.setTabPosition(QTabWidget.North)
        self.subtitle_tabs.setObjectName("subtitleTabs")
        
        # 原始字幕标签页
        original_tab = QWidget()
        original_tab.setObjectName("originalTab")
        original_layout = QVBoxLayout(original_tab)
        original_layout.setContentsMargins(8, 8, 8, 8)
        
        original_info = QLabel("语音识别结果")
        original_info.setStyleSheet("font-weight: bold; color: #28a745; margin-bottom: 5px;")
        
        self.original_subtitle_text = QTextEdit()
        self.original_subtitle_text.setObjectName("originalSubtitleText")
        self.original_subtitle_text.setPlaceholderText("原始字幕将在音频识别完成后显示...\n支持SRT时间戳格式")
        self.original_subtitle_text.setReadOnly(True)
        self.original_subtitle_text.setMinimumHeight(300)
        
        original_layout.addWidget(original_info)
        original_layout.addWidget(self.original_subtitle_text)
        
        # 转换后字幕标签页
        converted_tab = QWidget()
        converted_tab.setObjectName("convertedTab")
        converted_layout = QVBoxLayout(converted_tab)
        converted_layout.setContentsMargins(8, 8, 8, 8)
        
        converted_info = QLabel("转换翻译结果")
        converted_info.setStyleSheet("font-weight: bold; color: #0078D7; margin-bottom: 5px;")
        
        self.converted_subtitle_text = QTextEdit()
        self.converted_subtitle_text.setObjectName("convertedSubtitleText")
        self.converted_subtitle_text.setPlaceholderText("转换后的字幕将在处理完成后显示...\n包含翻译和时间同步信息")
        self.converted_subtitle_text.setReadOnly(True)
        self.converted_subtitle_text.setMinimumHeight(300)
        
        converted_layout.addWidget(converted_info)
        converted_layout.addWidget(self.converted_subtitle_text)
        
        self.subtitle_tabs.addTab(original_tab, "原始字幕")
        self.subtitle_tabs.addTab(converted_tab, "转换字幕")
        
        # 字幕操作按钮 - 只保留核心操作的图标
        subtitle_buttons = QHBoxLayout()
        subtitle_buttons.setSpacing(10)
        
        self.export_subtitle_btn = QPushButton("导出SRT")
        self.export_subtitle_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))  # 保存图标
        self.export_subtitle_btn.setObjectName("exportButton")
        self.export_subtitle_btn.setFixedHeight(32)
        self.export_subtitle_btn.setEnabled(False)
        self.export_subtitle_btn.clicked.connect(self.exportSubtitle)
        
        self.copy_subtitle_btn = QPushButton("复制")
        self.copy_subtitle_btn.setObjectName("copyButton")
        self.copy_subtitle_btn.setFixedHeight(32)
        self.copy_subtitle_btn.clicked.connect(self.copySubtitle)
        
        self.clear_subtitle_btn = QPushButton("清空")
        self.clear_subtitle_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))  # 删除图标
        self.clear_subtitle_btn.setObjectName("clearButton")
        self.clear_subtitle_btn.setFixedHeight(32)
        self.clear_subtitle_btn.clicked.connect(self.clearSubtitle)
        
        self.refresh_subtitle_btn = QPushButton("刷新")
        self.refresh_subtitle_btn.setObjectName("refreshButton")
        self.refresh_subtitle_btn.setFixedHeight(32)
        self.refresh_subtitle_btn.setToolTip("刷新字幕显示")
        
        subtitle_buttons.addWidget(self.export_subtitle_btn)
        subtitle_buttons.addWidget(self.copy_subtitle_btn)
        subtitle_buttons.addWidget(self.clear_subtitle_btn)
        subtitle_buttons.addWidget(self.refresh_subtitle_btn)
        subtitle_buttons.addStretch()
        
        layout.addWidget(self.subtitle_stats)
        layout.addWidget(self.subtitle_tabs, 1)
        layout.addLayout(subtitle_buttons)
        return group

    def createMenuBar(self):
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开视频', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.openVideoFile)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        settings_action = QAction('API 设置', self)
        settings_action.setShortcut('Ctrl+,')
        settings_action.triggered.connect(self.openSettings)
        tools_menu.addAction(settings_action)
        
        batch_action = QAction('批量处理', self)
        batch_action.setShortcut('Ctrl+B')
        batch_action.triggered.connect(self.openBatchProcessor)
        batch_action.setEnabled(True)
        tools_menu.addAction(batch_action)
        
        tools_menu.addSeparator()
        
        preview_action = QAction('预览效果', self)
        preview_action.setShortcut('Ctrl+P')
        preview_action.triggered.connect(self.openPreview)
        tools_menu.addAction(preview_action)
        
        # 视图菜单 - 修复缩放快捷键
        view_menu = menubar.addMenu('视图')
        
        zoom_menu = view_menu.addMenu('缩放')
        
        zoom_in_action = QAction('放大 (Ctrl+Shift+=)', self)
        zoom_in_action.setShortcut('Ctrl+Shift+=')
        zoom_in_action.triggered.connect(self.zoom_manager.zoomIn)
        zoom_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('缩小 (Ctrl+Shift+-)', self)
        zoom_out_action.setShortcut('Ctrl+Shift+-')
        zoom_out_action.triggered.connect(self.zoom_manager.zoomOut)
        zoom_menu.addAction(zoom_out_action)
        
        zoom_reset_action = QAction('重置缩放 (Ctrl+Shift+0)', self)
        zoom_reset_action.setShortcut('Ctrl+Shift+0')
        zoom_reset_action.triggered.connect(self.zoom_manager.resetZoom)
        zoom_menu.addAction(zoom_reset_action)
        
        view_menu.addSeparator()
        
        theme_menu = view_menu.addMenu('主题')
        
        light_theme_action = QAction('浅色主题', self)
        light_theme_action.triggered.connect(lambda: self.switchTheme('light'))
        theme_menu.addAction(light_theme_action)
        
        dark_theme_action = QAction('深色主题', self)
        dark_theme_action.triggered.connect(lambda: self.switchTheme('dark'))
        theme_menu.addAction(dark_theme_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)

    def createStatusBar(self):
        self.statusBar().showMessage("就绪")

    def load_stylesheet(self, filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print(f"警告: 样式文件 '{filename}' 未找到。将使用默认样式。")

    @pyqtSlot(str)
    def on_video_path_changed(self, path):
        self.video_path = path
        # 自动设置输出目录为视频所在目录
        if self.video_path and not self.output_path:
            self.output_path = os.path.dirname(self.video_path)
            self.output_path_label.setText(self.output_path)
        
        # 更新结果区域显示文字
        if hasattr(self, 'result_label'):
            self.updateResultDisplay(self.getInitialResultText(), "info")

    def selectOutputDir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_path or "")
        if dir_path:
            self.output_path = dir_path
            self.output_path_label.setText(self.output_path)
    
    def openSettings(self):
        # 立即反馈按钮点击
        self.settings_btn.setEnabled(False)
        self.statusBar().showMessage("正在打开设置...", 1000)
        QApplication.processEvents()
        
        try:
            dialog = SettingsDialog(self)
            dialog.exec_()
        finally:
            self.settings_btn.setEnabled(True)
            self.statusBar().showMessage("就绪")
    
    def openBatchProcessor(self):
        """打开批量处理对话框"""
        # 立即反馈按钮点击
        self.batch_btn.setEnabled(False)
        self.statusBar().showMessage("正在打开批量处理...", 1000)
        QApplication.processEvents()
        
        try:
            batch_processor.show_batch_dialog(self)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开批量处理窗口失败：{str(e)}")
        finally:
            self.batch_btn.setEnabled(True)
            self.statusBar().showMessage("就绪")
    
    def openVideoFile(self):
        """快捷键打开视频文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*)"
        )
        if file_path:
            self.file_input_widget.set_path(file_path)
    
    def openPreview(self):
        """预览功能"""
        # 立即反馈按钮点击
        self.preview_btn.setEnabled(False)
        self.statusBar().showMessage("正在加载预览...", 2000)
        QApplication.processEvents()  # 强制处理UI事件
        
        try:
            if not self.video_path:
                QMessageBox.warning(self, "警告", "请先选择视频文件！")
                return
            
            preview_dialog = VideoPreviewDialog(self.video_path, self)
            preview_dialog.exec_()
        finally:
            self.preview_btn.setEnabled(True)
            self.statusBar().showMessage("就绪")
    
    def switchTheme(self, theme):
        """切换主题"""
        if theme == 'dark':
            self.load_stylesheet("style_dark.qss")
        else:
            self.load_stylesheet("style.qss")
        
        # 保存主题设置
        try:
            config = {}
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['theme'] = theme
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存主题设置失败: {e}")
    
    def openResultFolder(self):
        """打开输出文件夹"""
        if hasattr(self, 'last_output_path') and self.last_output_path:
            import subprocess
            import platform
            
            # 确保路径存在
            if not os.path.exists(self.last_output_path):
                QMessageBox.warning(self, "错误", f"文件不存在：{self.last_output_path}")
                return
            
            # 获取文件所在目录
            if os.path.isfile(self.last_output_path):
                folder_path = os.path.dirname(self.last_output_path)
            else:
                folder_path = self.last_output_path
            
            # 确保目录存在
            if not os.path.exists(folder_path):
                QMessageBox.warning(self, "错误", f"目录不存在：{folder_path}")
                return
            
            try:
                if platform.system() == 'Windows':
                    # Windows: 使用explorer打开并选中文件
                    if os.path.isfile(self.last_output_path):
                        subprocess.run(['explorer', '/select,', self.last_output_path], check=True)
                    else:
                        subprocess.run(['explorer', folder_path], check=True)
                elif platform.system() == 'Darwin':  # macOS
                    if os.path.isfile(self.last_output_path):
                        subprocess.run(['open', '-R', self.last_output_path], check=True)
                    else:
                        subprocess.run(['open', folder_path], check=True)
                else:  # Linux
                    subprocess.run(['xdg-open', folder_path], check=True)
                    
                print(f"✅ 已打开文件夹: {folder_path}")
                    
            except subprocess.CalledProcessError as e:
                QMessageBox.warning(self, "错误", f"无法打开文件夹：{str(e)}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"打开文件夹时出错：{str(e)}")
        else:
            QMessageBox.warning(self, "提示", "没有可打开的输出文件夹")
    
    def playResultVideo(self):
        """播放结果视频"""
        if hasattr(self, 'last_output_path') and self.last_output_path:
            import subprocess
            import platform
            
            # 确保文件存在
            if not os.path.exists(self.last_output_path):
                QMessageBox.warning(self, "错误", f"视频文件不存在：{self.last_output_path}")
                return
            
            # 确保是文件而不是目录
            if not os.path.isfile(self.last_output_path):
                QMessageBox.warning(self, "错误", f"指定的路径不是文件：{self.last_output_path}")
                return
            
            try:
                if platform.system() == 'Windows':
                    # Windows: 使用默认程序打开
                    os.startfile(self.last_output_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', self.last_output_path], check=True)
                else:  # Linux
                    subprocess.run(['xdg-open', self.last_output_path], check=True)
                    
                print(f"✅ 已播放视频: {self.last_output_path}")
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法播放视频：{str(e)}")
                print(f"播放视频失败: {e}")
        else:
            QMessageBox.warning(self, "提示", "没有可播放的视频文件")
    
    def exportSubtitle(self):
        """导出字幕文件"""
        if not hasattr(self, 'last_subtitle_content') or not self.last_subtitle_content:
            QMessageBox.warning(self, "警告", "没有可导出的字幕内容")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存字幕文件", "", "SRT字幕文件 (*.srt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.last_subtitle_content)
                QMessageBox.information(self, "成功", f"字幕文件已保存到：{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存字幕文件失败：{str(e)}")
    
    def clearSubtitle(self):
        """清空字幕显示"""
        self.original_subtitle_text.clear()
        self.converted_subtitle_text.clear()
        if hasattr(self, 'last_subtitle_content'):
            delattr(self, 'last_subtitle_content')
        self.export_subtitle_btn.setEnabled(False)
        self.subtitle_stats.setText("统计: 已清空")
    
    def copySubtitle(self):
        """复制当前标签页的字幕内容"""
        clipboard = QApplication.clipboard()
        current_index = self.subtitle_tabs.currentIndex()
        
        if current_index == 0:  # 原始字幕
            content = self.original_subtitle_text.toPlainText()
            subtitle_type = "原始字幕"
        else:  # 转换后字幕
            content = self.converted_subtitle_text.toPlainText()
            subtitle_type = "转换后字幕"
        
        if content.strip():
            clipboard.setText(content)
            QMessageBox.information(self, "复制成功", f"{subtitle_type}已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", f"{subtitle_type}为空，无法复制")
    
    def updateSubtitleStats(self, content, subtitle_type):
        """更新字幕统计信息"""
        if not content:
            return
        
        lines = content.strip().split('\n')
        # 统计字幕条数（每3-4行为一条字幕：序号、时间、内容、空行）
        subtitle_count = len([line for line in lines if line.strip().isdigit()])
        
        # 统计字符数（去除时间戳和序号）
        import re
        clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', content)
        clean_text = re.sub(r'^\d+\n', '', clean_text, flags=re.MULTILINE)
        char_count = len(clean_text.replace('\n', '').replace(' ', ''))
        
        self.subtitle_stats.setText(f"统计: {subtitle_count}条字幕, {char_count}字符 ({subtitle_type})")
    
    def showAbout(self):
        """显示关于对话框"""
        about_text = """
        <h2>智能多语言视频语音转换系统 v3.0</h2>
        <p><b>AI-Powered Video Voice Dubbing</b></p>
        <p>基于人工智能的智能视频语音转换系统</p>
        <br>
        <p><b>主要功能：</b></p>
        <ul>
        <li>视频语音识别与转写</li>
        <li>多语言智能翻译</li>
        <li>高质量语音合成</li>
        <li>批量处理支持</li>
        <li>智能音频缓存</li>
        </ul>
        <br>
        <p><b>技术支持：</b></p>
        <p>科大讯飞语音云 | 百度翻译API</p>
        <p>PyQt5 | FFmpeg | MoviePy</p>
        <br>
        <p>© 2024 智能语音转换系统</p>
        """
        QMessageBox.about(self, "关于", about_text)
    
    def loadSavedTheme(self):
        """加载保存的主题设置"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    theme = config.get('theme', 'light')
                    if theme == 'dark':
                        self.load_stylesheet("style_dark.qss")
                    else:
                        self.load_stylesheet("style.qss")
            else:
                self.load_stylesheet("style.qss")
        except Exception as e:
            print(f"加载主题设置失败: {e}")
            self.load_stylesheet("style.qss")
    
    def calculateEstimatedTime(self):
        """计算预估处理时间（快速版本）"""
        try:
            if not self.video_path:
                return "无法估算"
            
            # 快速获取文件大小，避免UI阻塞
            file_size_mb = os.path.getsize(self.video_path) / (1024 * 1024)
            
            # 简化的时间估算，避免加载视频文件
            # 基于文件大小的粗略估算
            base_minutes = max(1, file_size_mb / 20)  # 每20MB大约1分钟处理时间
            
            # 转换类型影响
            conversion_type = self.conversion_combo.currentText()
            if "翻译" in conversion_type or conversion_type == "智能转换":
                base_minutes *= 1.5
            
            # 质量影响
            quality = self.quality_combo.currentText()
            quality_multiplier = {
                "标准质量": 0.8,
                "高质量": 1.0,
                "超清质量": 1.3
            }.get(quality, 1.0)
            base_minutes *= quality_multiplier
            
            # 确保最少1分钟，最多30分钟
            base_minutes = max(1, min(30, base_minutes))
            
            # 格式化显示
            total_seconds = int(base_minutes * 60)
            if total_seconds < 60:
                return f"{total_seconds}秒"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                if seconds > 0:
                    return f"{minutes}分{seconds}秒"
                else:
                    return f"{minutes}分钟"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}小时{minutes}分钟"
                
        except Exception as e:
            print(f"计算预估时间失败: {e}")
            return "2-5分钟"
    
    def parseTimeToSeconds(self, time_str):
        """将时间字符串转换为秒数"""
        try:
            total_seconds = 0
            if "小时" in time_str:
                hours = int(time_str.split("小时")[0])
                total_seconds += hours * 3600
                time_str = time_str.split("小时")[1]
            if "分" in time_str:
                minutes = int(time_str.split("分")[0])
                total_seconds += minutes * 60
                time_str = time_str.split("分")[1]
            if "秒" in time_str:
                seconds = int(time_str.split("秒")[0])
                total_seconds += seconds
            return total_seconds
        except:
            return 300  # 默认5分钟
        
    def startProcessing(self):
        # 立即禁用按钮，提供用户反馈
        self.process_btn.setEnabled(False)
        self.process_btn.setText("准备中...")
        QApplication.processEvents()
        
        if not self.video_path or not self.output_path:
            QMessageBox.warning(self, "警告", "请先选择视频文件和输出目录！")
            self.process_btn.setEnabled(True)
            self.process_btn.setText("开始转换")
            return
        
        self.set_controls_enabled(False)
        
        # 计算预估时间
        estimated_time = self.calculateEstimatedTime()
        self.status_label.setText(f"开始处理... 预计需要 {estimated_time}")
        
        # 更新结果显示为处理中状态
        processing_text = f"🔄 正在处理视频文件...\n\n📁 输入: {os.path.basename(self.video_path)}\n⏱️ 预计时间: {estimated_time}\n\n请耐心等待处理完成 ➤➤➤"
        self.updateResultDisplay(processing_text, "processing")
        
        # 恢复按钮文本但保持禁用状态
        self.process_btn.setText("处理中...")
        
        conversion_type = self.conversion_combo.currentText()
        
        # 收集语音参数 - 适配新的滑块组件
        voice_params = {
            'voice_type': self.voice_combo.currentText().split(' - ')[0],
            'speed': self.speed_slider.value(),
            'volume': self.volume_slider.value(),
            'quality': self.quality_combo.currentText()
        }
        
        self.process_thread = ProcessThread(self.video_path, self.output_path, conversion_type, voice_params)
        self.process_thread.progress.connect(self.update_progress)
        self.process_thread.finished.connect(self.on_process_finished)
        self.process_thread.subtitle_ready.connect(self.on_subtitle_ready)
        self.process_thread.start()
        
        # 启动倒计时显示
        self.start_time = time.time()
        self.estimated_total_time = self.parseTimeToSeconds(estimated_time)
        
        # 创建定时器用于更新进度显示
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.updateProgressDisplay)
        self.progress_timer.start(1000)  # 每秒更新一次
    
    def updateProgressDisplay(self):
        """更新进度显示"""
        if not hasattr(self, 'start_time') or not hasattr(self, 'progress_timer'):
            return
            
        if not self.process_thread or not self.process_thread.isRunning():
            if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
                self.progress_timer.stop()
            return
        
        elapsed_time = time.time() - self.start_time
        current_progress = self.progress_bar.value()
        
        if current_progress > 0 and current_progress < 100:
            # 根据当前进度估算剩余时间
            estimated_total = (elapsed_time / current_progress) * 100
            remaining_time = max(0, estimated_total - elapsed_time)
            
            remaining_minutes = int(remaining_time // 60)
            remaining_seconds = int(remaining_time % 60)
            
            if remaining_minutes > 0:
                remaining_text = f"剩余约 {remaining_minutes}分{remaining_seconds}秒"
            else:
                remaining_text = f"剩余约 {remaining_seconds}秒"
            
            # 获取当前状态文本的基础部分
            current_text = self.status_label.text()
            if " (剩余约" in current_text:
                base_text = current_text.split(" (剩余约")[0]
            else:
                base_text = current_text
            
            self.status_label.setText(f"{base_text} ({remaining_text})")
    
    def stopProcessing(self):
        if self.process_thread and self.process_thread.isRunning():
            self.process_thread.stop()
            self.status_label.setText("正在停止，请稍候...")
            self.stop_btn.setEnabled(False) # 防止重复点击
            
        # 停止进度定时器
        if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
            self.progress_timer.stop()
    
    @pyqtSlot(int, str)
    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        
        # 计算剩余时间
        if hasattr(self, 'start_time') and hasattr(self, 'estimated_total_time') and value > 0:
            elapsed_time = time.time() - self.start_time
            if value < 100:
                # 根据进度估算剩余时间
                estimated_remaining = (elapsed_time / value) * (100 - value)
                remaining_minutes = int(estimated_remaining // 60)
                remaining_seconds = int(estimated_remaining % 60)
                
                if remaining_minutes > 0:
                    remaining_text = f" (剩余约 {remaining_minutes}分{remaining_seconds}秒)"
                else:
                    remaining_text = f" (剩余约 {remaining_seconds}秒)"
                
                self.status_label.setText(text + remaining_text)
            else:
                self.status_label.setText(text)
        else:
            self.status_label.setText(text)

    @pyqtSlot(str, str)
    def on_subtitle_ready(self, subtitle_content, subtitle_type):
        """字幕准备就绪回调"""
        try:
            # 处理字幕内容编码问题
            if isinstance(subtitle_content, bytes):
                try:
                    subtitle_content = subtitle_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        subtitle_content = subtitle_content.decode('gbk')
                    except UnicodeDecodeError:
                        subtitle_content = subtitle_content.decode('windows-1252', errors='ignore')
            
            # 清理字幕内容
            cleaned_content = '\n'.join(line.strip() for line in str(subtitle_content).split('\n') if line.strip())
            
            if subtitle_type == "original":
                self.original_subtitle_text.setPlainText(cleaned_content)
                self.subtitle_tabs.setCurrentIndex(0)  # 切换到原始字幕页
                self.updateSubtitleStats(cleaned_content, "原始字幕")
                print(f"原始字幕已显示: {len(cleaned_content)} 字符")
                
                # 滚动到顶部
                cursor = self.original_subtitle_text.textCursor()
                cursor.movePosition(cursor.Start)
                self.original_subtitle_text.setTextCursor(cursor)
                
            elif subtitle_type == "converted":
                self.converted_subtitle_text.setPlainText(cleaned_content)
                self.last_subtitle_content = cleaned_content
                self.export_subtitle_btn.setEnabled(True)
                self.subtitle_tabs.setCurrentIndex(1)  # 切换到转换后字幕页
                self.updateSubtitleStats(cleaned_content, "转换后字幕")
                print(f"转换后字幕已显示: {len(cleaned_content)} 字符")
                
                # 滚动到顶部
                cursor = self.converted_subtitle_text.textCursor()
                cursor.movePosition(cursor.Start)
                self.converted_subtitle_text.setTextCursor(cursor)
                
        except Exception as e:
            print(f"显示字幕时出错: {e}")
            # 显示错误信息
            error_msg = f"字幕显示错误: {str(e)}\n原始内容长度: {len(str(subtitle_content))}"
            if subtitle_type == "original":
                self.original_subtitle_text.setPlainText(error_msg)
            elif subtitle_type == "converted":
                self.converted_subtitle_text.setPlainText(error_msg)

    @pyqtSlot(bool, str)
    def on_process_finished(self, success, message):
        # 停止进度定时器
        if hasattr(self, 'progress_timer') and self.progress_timer.isActive():
            self.progress_timer.stop()
            
        self.set_controls_enabled(True)
        
        if success:
            # message现在是文件路径
            self.last_output_path = message
            
            # 获取文件信息
            try:
                file_size = os.path.getsize(message) / (1024 * 1024)
                file_name = os.path.basename(message)
                dir_name = os.path.dirname(message)
                
                result_text = f"""✅ 处理成功完成！

📁 输出文件: {file_name}
📂 保存目录: {dir_name}
📏 文件大小: {file_size:.1f} MB

您可以点击下方按钮打开文件夹或直接播放视频。"""
            except:
                result_text = f"""✅ 处理成功完成！

📁 输出文件: {message}

您可以点击下方按钮打开文件夹或直接播放视频。"""
            
            self.updateResultDisplay(result_text, "success")
            
            # 启用结果操作按钮
            self.open_result_btn.setEnabled(True)
            self.play_result_btn.setEnabled(True)
            
            QMessageBox.information(self, "处理完成", f"视频处理成功完成！\n\n输出文件：{os.path.basename(message)}")
            self.status_label.setText("处理完成")
        else:
            # 更新结果显示
            self.updateResultDisplay(f"""❌ 处理失败

错误信息: {message}

请检查输入文件和设置，然后重试。如果问题持续存在，请查看控制台输出获取更多详细信息。""", "error")
            
            QMessageBox.critical(self, "处理失败", f"视频处理失败：\n\n{message}")
            self.status_label.setText("处理失败")
        
        self.process_thread = None

    def set_controls_enabled(self, enabled):
        """统一设置控件的可用状态"""
        self.process_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(not enabled)
        
        # 恢复处理按钮文本
        if enabled:
            self.process_btn.setText("开始转换")
        
        self.file_input_widget.setEnabled(enabled)
        self.conversion_combo.setEnabled(enabled)
        self.voice_combo.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)
        self.volume_slider.setEnabled(enabled)
        self.quality_combo.setEnabled(enabled)
        self.menuBar().setEnabled(enabled)

    def resizeEvent(self, event):
        """窗口大小改变时调整布局"""
        super().resizeEvent(event)
        # 根据窗口大小动态调整边距
        if hasattr(self, 'centralWidget'):
            layout = self.centralWidget().layout()
            if layout:
                base_margin = max(10, min(30, self.width() // 40))
                layout.setContentsMargins(base_margin, base_margin, base_margin, base_margin)
    
    def closeEvent(self, event):
        """关闭窗口时，确保线程已停止"""
        if self.process_thread and self.process_thread.isRunning():
            reply = QMessageBox.question(self, '确认退出', 
                                       "处理任务仍在进行中，确定要退出吗？", 
                                       QMessageBox.Yes | QMessageBox.No, 
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stopProcessing()
                self.process_thread.wait(5000) # 等待最多5秒
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    # 设置控制台编码为UTF-8，修复乱码问题
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # NEW: 启用高DPI缩放，让界面在高清屏上更清晰
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("智能视频语音转换系统")
    app.setApplicationVersion("3.1")
    
    # 设置应用程序图标
    try:
        custom_icon = app_icon.create_app_icon()
        app.setWindowIcon(custom_icon)
    except:
        # 备用方案：使用系统图标
        app.setWindowIcon(app.style().standardIcon(QStyle.SP_MediaPlay))
    
    # NEW: 使用现代字体
    font = QFontDatabase.systemFont(QFontDatabase.GeneralFont)
    app.setFont(font)

    window = EnhancedMainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
 