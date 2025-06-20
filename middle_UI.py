# -*- coding: utf-8 -*-
"""
语音替换工具 v1.0
- 简化UI设计，专注核心功能
- 移除字幕预览和编辑功能
- 优化布局适配不同屏幕尺寸
- 专为演示优化
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
import unified_speech_synthesis
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
        return os.path.normpath(os.path.join(self.base_path, f'{self.file_prefix}_subtitle.srt')).replace('\\', '/')
    
    def get_audio_path(self):
        """获取提取的音频文件路径"""
        return os.path.normpath(os.path.join(self.base_path, f'{self.file_prefix}_extractedAudio.wav')).replace('\\', '/')
    
    def get_output_video_path(self, base_name, conversion_suffix):
        """获取输出视频文件路径"""
        name, ext = os.path.splitext(base_name)
        return os.path.normpath(os.path.join(self.base_path, f"{name}_{conversion_suffix}{ext}")).replace('\\', '/')
    
    def ensure_directory_exists(self):
        """确保基础目录存在"""
        try:
            os.makedirs(self.base_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败 {self.base_path}: {e}")
            return False

# --- 增强的滑块控件 ---
class EnhancedSlider(QWidget):
    """增强的滑块组件，支持箭头调节和双击输入"""
    valueChanged = pyqtSignal(int)
    
    def __init__(self, minimum=0, maximum=100, value=50, step=5, suffix="%", parent=None):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.suffix = suffix
        self.setupUI()
        self.setValue(value)
        
    def setupUI(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 减少按钮
        self.dec_btn = QPushButton("◀")
        self.dec_btn.setFixedSize(25, 25)
        self.dec_btn.clicked.connect(self.decreaseValue)
        
        # 滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(self.minimum)
        self.slider.setMaximum(self.maximum)
        self.slider.valueChanged.connect(self.onSliderChanged)
        
        # 数值标签（可双击编辑）
        self.label = QLabel()
        self.label.setMinimumWidth(60)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                border: 1px solid #ddd;
                border-radius: 3px;
                background: white;
                padding: 2px;
            }
            QLabel:hover {
                border-color: #007ACC;
                background: #f0f8ff;
            }
        """)
        self.label.installEventFilter(self)
        
        # 增加按钮
        self.inc_btn = QPushButton("▶")
        self.inc_btn.setFixedSize(25, 25)
        self.inc_btn.clicked.connect(self.increaseValue)
        
        layout.addWidget(self.dec_btn)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.label)
        layout.addWidget(self.inc_btn)
        
        self.setLayout(layout)
    
    def eventFilter(self, obj, event):
        if obj == self.label and event.type() == QEvent.MouseButtonDblClick:
            self.openInputDialog()
            return True
        return super().eventFilter(obj, event)
    
    def openInputDialog(self):
        current_value = self.slider.value()
        value, ok = QInputDialog.getInt(
            self, "设置数值", 
            f"请输入数值 ({self.minimum}-{self.maximum}):",
            current_value, self.minimum, self.maximum
        )
        if ok:
            self.setValue(value)
    
    def decreaseValue(self):
        new_value = max(self.minimum, self.slider.value() - self.step)
        self.setValue(new_value)
    
    def increaseValue(self):
        new_value = min(self.maximum, self.slider.value() + self.step)
        self.setValue(new_value)
    
    def onSliderChanged(self, value):
        self.label.setText(f"{value}{self.suffix}")
        self.valueChanged.emit(value)
    
    def setValue(self, value):
        value = max(self.minimum, min(self.maximum, value))
        self.slider.setValue(value)
        self.label.setText(f"{value}{self.suffix}")
    
    def value(self):
        return self.slider.value()

# --- 文件输入组件 ---
class FileInputWidget(QWidget):
    """一个支持拖拽和点击选择文件的自定义组件"""
    pathChanged = pyqtSignal(str)
    
    def __init__(self, description="拖拽视频文件至此，或点击浏览"):
        super().__init__()
        self.description = description
        self.file_path = ""
        
        # 设置接受拖拽
        self.setAcceptDrops(True)
        
        # 设置固定高度和样式
        self.setFixedHeight(40)
        
        # 创建布局
        layout = QVBoxLayout()
        self.label = QLabel(self.description)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                event.acceptProposedAction()
                self.setStyleSheet("""
                    FileInputWidget {
                        border: 2px solid #007ACC;
                        background-color: #e6f3ff;
                    }
                """)
    
    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.setStyleSheet("""
            FileInputWidget {
                border: 2px dashed #cccccc;
                background-color: #fafafa;
            }
            FileInputWidget:hover {
                border-color: #007ACC;
                background-color: #f0f8ff;
            }
        """)
    
    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.set_path(files[0])
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择视频文件", "",
                "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv);;所有文件 (*)"
            )
            if file_path:
                self.set_path(file_path)
    
    def set_path(self, path):
        self.file_path = path
        self.label.setText(f"已选择: {os.path.basename(path)}")
        self.pathChanged.emit(path)

# --- 简化的设置对话框 ---
class MiddleSettingsDialog(QDialog):
    """设置对话框 - 简化本"""
    configUpdated = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        self.loadSettings()
        
    def setupUi(self):
        self.setWindowTitle("设置")
        self.setFixedSize(600, 500)
        
        layout = QVBoxLayout()
        
        # 创建选项卡控件
        tab_widget = QTabWidget()
        
        # API设置选项卡
        api_tab = QWidget()
        api_layout = QVBoxLayout()
        api_layout.setSpacing(8)
        
        # 科大讯飞语音转写API配置
        stt_group = QGroupBox("科大讯飞语音转写API (STT)")
        stt_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin: 5px 0;
                padding-top: 10px;
                background-color: #fafafa;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
        """)
        stt_layout = QFormLayout()
        stt_layout.setVerticalSpacing(8)
        stt_layout.setHorizontalSpacing(8)
        
        self.xunfei_appid = QLineEdit()
        self.xunfei_appid.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        self.xunfei_apikey = QLineEdit()
        self.xunfei_apikey.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        self.xunfei_apisecret = QLineEdit()
        self.xunfei_apisecret.setEchoMode(QLineEdit.Password)
        self.xunfei_apisecret.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        
        stt_layout.addRow("APPID:", self.xunfei_appid)
        stt_layout.addRow("APIKey:", self.xunfei_apikey)
        stt_layout.addRow("APISecret:", self.xunfei_apisecret)
        stt_group.setLayout(stt_layout)
        
        # 科大讯飞语音合成API配置
        tts_group = QGroupBox("科大讯飞语音合成API (TTS)")
        tts_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin: 5px 0;
                padding-top: 10px;
                background-color: #fafafa;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
        """)
        tts_layout = QFormLayout()
        tts_layout.setVerticalSpacing(8)
        tts_layout.setHorizontalSpacing(8)
        
        self.xunfei_tts_appid = QLineEdit()
        self.xunfei_tts_appid.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        self.xunfei_tts_apikey = QLineEdit()
        self.xunfei_tts_apikey.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        self.xunfei_tts_apisecret = QLineEdit()
        self.xunfei_tts_apisecret.setEchoMode(QLineEdit.Password)
        self.xunfei_tts_apisecret.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        
        tts_layout.addRow("APPID:", self.xunfei_tts_appid)
        tts_layout.addRow("APIKey:", self.xunfei_tts_apikey)
        tts_layout.addRow("APISecret:", self.xunfei_tts_apisecret)
        tts_group.setLayout(tts_layout)
        
        # 百度翻译API配置
        baidu_group = QGroupBox("百度翻译API")
        baidu_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin: 5px 0;
                padding-top: 10px;
                background-color: #fafafa;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
        """)
        baidu_layout = QFormLayout()
        baidu_layout.setVerticalSpacing(8)
        baidu_layout.setHorizontalSpacing(8)
        
        self.baidu_appid = QLineEdit()
        self.baidu_appid.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        self.baidu_appkey = QLineEdit()
        self.baidu_appkey.setEchoMode(QLineEdit.Password)
        self.baidu_appkey.setStyleSheet("QLineEdit { padding: 4px; font-size: 11px; }")
        
        baidu_layout.addRow("APPID:", self.baidu_appid)
        baidu_layout.addRow("AppKey:", self.baidu_appkey)
        baidu_group.setLayout(baidu_layout)
        
        api_layout.addWidget(stt_group)
        api_layout.addWidget(tts_group)
        api_layout.addWidget(baidu_group)
        api_layout.addStretch()
        api_tab.setLayout(api_layout)
        
        # 语音设置选项卡（简化）
        voice_tab = QWidget()
        voice_layout = QVBoxLayout()
        voice_layout.setSpacing(8)
        
        # 语音参数分组
        voice_params_group = QGroupBox("语音参数设置")
        voice_params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin: 5px 0;
                padding-top: 10px;
                background-color: #fafafa;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
        """)
        voice_params_layout = QFormLayout()
        voice_params_layout.setVerticalSpacing(8)
        voice_params_layout.setHorizontalSpacing(8)
        
        # 语音速度
        self.voice_speed = EnhancedSlider(50, 200, 100, 5, "")
        voice_params_layout.addRow("语音速度:", self.voice_speed)
        
        # 语音音量
        self.voice_volume = EnhancedSlider(0, 100, 80, 5, "")
        voice_params_layout.addRow("语音音量:", self.voice_volume)
        
        voice_params_group.setLayout(voice_params_layout)
        
        # 发音人和质量分组
        quality_group = QGroupBox("发音人和质量设置")
        quality_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin: 5px 0;
                padding-top: 10px;
                background-color: #fafafa;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #333333;
            }
        """)
        quality_layout = QFormLayout()
        quality_layout.setVerticalSpacing(8)
        quality_layout.setHorizontalSpacing(8)
        
        # 中文发音人
        self.voice_type_cn = QComboBox()
        self.voice_type_cn.setStyleSheet("QComboBox { padding: 4px; font-size: 11px; }")
        self.voice_type_cn.addItems([
            "xiaoyan (女声·亲和)",
            "aisjiuxu (男声·专业)",
            "aisxping (男声·成熟)",
            "aisjinger (女声·温暖)",
            "aisbabyxu (童声·可爱)"
        ])
        quality_layout.addRow("中文发音人:", self.voice_type_cn)
        
        # 英文发音人
        self.voice_type_en = QComboBox()
        self.voice_type_en.setStyleSheet("QComboBox { padding: 4px; font-size: 11px; }")
        self.voice_type_en.addItems([
            "x4_EnUs_Laura_education (女声·教育)",
            "x4_EnUs_Alex_education (男声·教育)",
            "x4_EnUs_Emma_formal (女声·正式)",
            "x4_EnUs_Chris_formal (男声·正式)"
        ])
        quality_layout.addRow("英文发音人:", self.voice_type_en)
        
        # 输出质量
        self.output_quality = QComboBox()
        self.output_quality.setStyleSheet("QComboBox { padding: 4px; font-size: 11px; }")
        self.output_quality.addItems(["标准质量", "高质量", "超清质量"])
        self.output_quality.setCurrentText("高质量")
        quality_layout.addRow("输出质量:", self.output_quality)
        
        # 音频缓存
        self.enable_cache = QCheckBox("启用音频缓存（减少重复API调用）")
        self.enable_cache.setStyleSheet("QCheckBox { font-size: 11px; }")
        self.enable_cache.setChecked(True)
        quality_layout.addRow("缓存设置:", self.enable_cache)
        
        quality_group.setLayout(quality_layout)
        
        voice_layout.addWidget(voice_params_group)
        voice_layout.addWidget(quality_group)
        voice_layout.addStretch()
        voice_tab.setLayout(voice_layout)
        
        # 添加选项卡
        tab_widget.addTab(api_tab, "API设置")
        tab_widget.addTab(voice_tab, "语音设置")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 配置管理按钮
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
        
        # 主要操作按钮
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self.saveSettings)
        cancel_btn.clicked.connect(self.reject)
        
        # 按钮样式
        button_style = """
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """
        save_btn.setStyleSheet(button_style)
        
        cancel_style = """
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """
        cancel_btn.setStyleSheet(cancel_style)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(tab_widget)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def loadSettings(self):
        """加载设置"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # API设置
                self.xunfei_appid.setText(config.get('xunfei_appid', ''))
                self.xunfei_apikey.setText(config.get('xunfei_apikey', ''))
                self.xunfei_apisecret.setText(config.get('xunfei_apisecret', ''))
                
                self.xunfei_tts_appid.setText(config.get('xunfei_tts_appid', ''))
                self.xunfei_tts_apikey.setText(config.get('xunfei_tts_apikey', ''))
                self.xunfei_tts_apisecret.setText(config.get('xunfei_tts_apisecret', ''))
                
                self.baidu_appid.setText(config.get('baidu_appid', ''))
                self.baidu_appkey.setText(config.get('baidu_appkey', ''))
                
                # 语音设置
                self.voice_speed.setValue(config.get('voice_speed', 100))
                self.voice_volume.setValue(config.get('voice_volume', 80))
                
                voice_type = config.get('voice_type', 'xiaoyan')
                if 'En' in voice_type:
                    self.voice_type_en.setCurrentText(voice_type + " (女声·教育)" if voice_type == "x4_EnUs_Laura_education" else voice_type)
                else:
                    self.voice_type_cn.setCurrentText(voice_type + " (女声·亲和)" if voice_type == "xiaoyan" else voice_type)
                
                self.output_quality.setCurrentText(config.get('output_quality', '高质量'))
                self.enable_cache.setChecked(config.get('enable_cache', True))
                
        except Exception as e:
            print(f"加载设置失败: {e}")
    
    def saveSettings(self):
        """保存设置"""
        try:
            config = {
                'xunfei_appid': self.xunfei_appid.text(),
                'xunfei_apikey': self.xunfei_apikey.text(),
                'xunfei_apisecret': self.xunfei_apisecret.text(),
                'xunfei_tts_appid': self.xunfei_tts_appid.text(),
                'xunfei_tts_apikey': self.xunfei_tts_apikey.text(),
                'xunfei_tts_apisecret': self.xunfei_tts_apisecret.text(),
                'baidu_appid': self.baidu_appid.text(),
                'baidu_appkey': self.baidu_appkey.text(),
                'voice_speed': self.voice_speed.value(),
                'voice_volume': self.voice_volume.value(),
                'voice_type': self.voice_type_cn.currentText().split(' ')[0],
                'voice_type_en': self.voice_type_en.currentText().split(' ')[0],
                'output_quality': self.output_quality.currentText(),
                'enable_cache': self.enable_cache.isChecked(),
                'subtitle_mode': '不嵌入字幕'  # 默认不嵌入字幕
            }
            
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.configUpdated.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存设置失败: {e}")
    
    def exportSettings(self):
        """导出设置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出设置", "config_backup.json",
            "JSON文件 (*.json);;所有文件 (*)"
        )
        if file_path:
            try:
                import shutil
                shutil.copy('config.json', file_path)
                QMessageBox.information(self, "成功", "设置导出成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {e}")
    
    def importSettings(self):
        """导入设置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入设置", "", 
            "JSON文件 (*.json);;所有文件 (*)"
        )
        if file_path:
            try:
                import shutil
                shutil.copy(file_path, 'config.json')
                self.loadSettings()
                QMessageBox.information(self, "成功", "设置导入成功！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导入失败: {e}")
    
    def resetSettings(self):
        """重置为默认设置"""
        reply = QMessageBox.question(
            self, "确认重置", 
            "确定要重置所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists('config.json'):
                    os.remove('config.json')
                self.loadSettings()
                QMessageBox.information(self, "成功", "设置已重置为默认值！")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"重置失败: {e}") 

# --- 简化的处理线程 ---
class MiddleProcessThread(QThread):
    """处理线程 - 简化本，无字幕功能"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    paused = pyqtSignal()
    resumed = pyqtSignal()
    
    def __init__(self, video_path, save_path, conversion_type, voice_params=None):
        super().__init__()
        self.video_path = video_path
        self.save_path = save_path
        self.conversion_type = conversion_type
        self.voice_params = voice_params or {}
        
        self._stop_requested = False
        self._pause_requested = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # 初始状态不暂停
        
        # 路径管理器
        self.path_manager = SubtitlePathManager(save_path, video_path)
    
    def detectLanguage(self, text):
        """检测文本语言 - 简化版本"""
        import re
        
        # 移除特殊字符和数字，只保留字母
        clean_text = re.sub(r'[^\w\s]', ' ', text)
        clean_text = re.sub(r'\d+', ' ', clean_text)
        words = clean_text.split()
        
        if not words:
            return "unknown"
        
        # 统计中英文字符
        chinese_chars = 0
        english_chars = 0
        total_chars = 0
        
        for word in words:
            for char in word:
                total_chars += 1
                if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                    chinese_chars += 1
                elif char.isalpha():  # 英文字符
                    english_chars += 1
        
        if total_chars == 0:
            return "unknown"
        
        chinese_ratio = chinese_chars / total_chars
        english_ratio = english_chars / total_chars
        
        print(f"语言检测 - 中文比例: {chinese_ratio:.2f}, 英文比例: {english_ratio:.2f}")
        
        # 判断主要语言
        if chinese_ratio > 0.3:
            return "chinese"
        elif english_ratio > 0.5:
            return "english"
        else:
            return "unknown"
    
    def run(self):
        """主处理流程"""
        try:
            self.progress.emit(0, "开始处理视频...")
            
            # 确保输出目录存在
            if not self.path_manager.ensure_directory_exists():
                self.finished.emit(False, "无法创建输出目录")
                return
            
            # 第一步：提取音频（15%）
            self._check_pause_state()
            if self._stop_requested:
                return
            
            self.progress.emit(15, "正在提取音频...")
            audio_path = self.path_manager.get_audio_path()
            
            try:
                import moviepy.editor as mp
                video = mp.VideoFileClip(self.video_path)
                if video.audio is None:
                    self.finished.emit(False, "视频文件没有音频轨道")
                    return
                video.audio.write_audiofile(audio_path, verbose=False, logger=None)
                video.close()
                print(f"音频提取完成: {audio_path}")
            except Exception as e:
                self.finished.emit(False, f"音频提取失败: {str(e)}")
                return
            
            # 第二步：语音识别生成字幕（30%）
            self._check_pause_state()
            if self._stop_requested:
                return
            
            self.progress.emit(30, "正在进行语音识别...")
            original_subtitle_file = self.path_manager.get_original_subtitle_path()
            
            try:
                import video_to_txt
                video_to_txt.generateSubtitle(audio_path, original_subtitle_file)
                print(f"字幕生成完成: {original_subtitle_file}")
            except Exception as e:
                self.finished.emit(False, f"语音识别失败: {str(e)}")
                return
            
            # 智能转换：检测语言并确定实际转换类型
            actual_conversion_type = self.conversion_type
            if self.conversion_type == "智能转换":
                self._check_pause_state()
                if self._stop_requested:
                    return
                
                self.progress.emit(45, "正在分析语言...")
                
                try:
                    # 读取字幕文件进行语言检测
                    with open(original_subtitle_file, 'r', encoding='utf-8') as f:
                        subtitle_content = f.read()
                    
                    detected_lang = self.detectLanguage(subtitle_content)
                    
                    if detected_lang == "chinese":
                        actual_conversion_type = "中文转英文"
                        print("智能转换：检测到中文，转换为 中文转英文")
                    elif detected_lang == "english":
                        actual_conversion_type = "英文转中文"
                        print("智能转换：检测到英文，转换为 英文转中文")
                    else:
                        actual_conversion_type = "英文转中文"  # 默认
                        print("智能转换：未能确定语言，使用默认 英文转中文")
                        
                except Exception as e:
                    print(f"语言检测失败: {e}")
                    actual_conversion_type = "英文转中文"  # 默认
            
            # 第三步：语音合成（60%）
            self._check_pause_state()
            if self._stop_requested:
                return
            
            self.progress.emit(60, "正在生成新的语音...")
            
            def progress_callback(progress, message):
                if self._stop_requested:
                    return
                # 将合成进度映射到60-85%
                mapped_progress = 60 + int(progress * 0.25)
                self.progress.emit(mapped_progress, f"语音合成: {message}")
            
            try:
                synthesis = unified_speech_synthesis.UnifiedSpeechSynthesis()
                
                # 设置缓存状态
                cache_enabled = self.voice_params.get('enable_cache', True)
                synthesis.set_cache_enabled(cache_enabled)
                
                # 获取语音参数
                voice_speed = self.voice_params.get('voice_speed', 100)
                voice_volume = self.voice_params.get('voice_volume', 80)
                quality = self.voice_params.get('output_quality', '高质量')
                
                # 根据实际转换类型选择发音人
                if self.voice_params.get('voice_type') == "auto_detect":
                    # 智能转换：根据检测到的实际转换类型选择发音人
                    if actual_conversion_type in ["英文转英文", "中文转英文"]:
                        voice_type = self.voice_params.get('voice_type_en', 'x4_EnUs_Laura_education')
                    else:  # 中文转中文, 英文转中文
                        voice_type = self.voice_params.get('voice_type_cn', 'xiaoyan')
                else:
                    # 固定转换类型：根据转换类型选择发音人
                    if actual_conversion_type in ["英文转英文", "中文转英文"]:
                        voice_type = self.voice_params.get('voice_type_en', 'x4_EnUs_Laura_education')
                    else:  # 中文转中文, 英文转中文
                        voice_type = self.voice_params.get('voice_type_cn', 'xiaoyan')
                
                # 处理视频
                result = synthesis.process_video(
                    self.video_path,
                    original_subtitle_file,
                    self.save_path,
                    conversion_type=actual_conversion_type,
                    voice_type=voice_type,
                    speed=voice_speed,
                    volume=voice_volume,
                    progress_callback=progress_callback,
                    quality=quality
                )
                
                if not result:
                    self.finished.emit(False, "语音合成处理失败")
                    return
                    
            except Exception as e:
                self.finished.emit(False, f"语音合成失败: {str(e)}")
                return
            
            # 第四步：完成处理（100%）
            self._check_pause_state()
            if self._stop_requested:
                return
            
            self.progress.emit(100, "处理完成！")
            
            # 查找生成的输出文件
            video_name = os.path.splitext(os.path.basename(self.video_path))[0]
            conversion_suffixes = {
                "智能转换": "smart",
                "英文转中文": "英文转中文",
                "中文转英文": "中文转英文", 
                "英文转英文": "英文转英文",
                "中文转中文": "中文转中文"
            }
            
            # 使用实际转换类型来确定后缀
            suffix = conversion_suffixes.get(actual_conversion_type, "converted")
            expected_output = self.path_manager.get_output_video_path(
                os.path.basename(self.video_path), suffix
            )
            
            if os.path.exists(expected_output):
                self.finished.emit(True, f"处理成功完成！\n输出文件: {expected_output}")
            else:
                self.finished.emit(True, f"处理完成！请检查输出目录: {self.save_path}")
                
        except Exception as e:
            self.finished.emit(False, f"处理过程中发生错误: {str(e)}")
        finally:
            # 清理临时文件
            try:
                self.path_manager.cleanup_temp_files()
            except Exception as e:
                print(f"清理临时文件时出错: {e}")
    
    def pause(self):
        """暂停处理"""
        self._pause_requested = True
        self._pause_event.clear()
        self.paused.emit()
    
    def resume(self):
        """恢复处理"""
        self._pause_requested = False
        self._pause_event.set()
        self.resumed.emit()
    
    def stop(self):
        """停止处理"""
        self._stop_requested = True
        self._pause_event.set()  # 确保线程不会卡在暂停状态
        self.terminate()
    
    def _check_pause_state(self):
        """检查暂停状态"""
        if self._pause_requested:
            self._pause_event.wait()  # 等待恢复信号 

# --- 主窗口 ---
class MiddleMainWindow(QMainWindow):
    """主窗口 - 简化UI，专注核心功能"""
    
    def __init__(self):
        super().__init__()
        self.config = {}
        self.process_thread = None
        self.is_processing = False
        self.is_paused = False
        
        # 加载配置
        self.loadConfig()
        
        # 设置窗口
        self.setupUi()
        self.loadConfigToUI()
        self.centerWindow()
        
        # 设置窗口图标
        try:
            self.setWindowIcon(app_icon.get_app_icon())
        except Exception as e:
            print(f"设置图标失败: {e}")
    
    def loadConfig(self):
        """加载配置文件"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                # 默认配置
                self.config = {
                    'voice_speed': 100,
                    'voice_volume': 80,
                    'voice_type': 'xiaoyan',
                    'voice_type_en': 'x4_EnUs_Laura_education',
                    'output_quality': '高质量',
                    'enable_cache': True,
                    'subtitle_mode': '不嵌入字幕'
                }
        except Exception as e:
            print(f"加载配置失败: {e}")
            self.config = {}
    
    def loadConfigToUI(self):
        """将配置加载到UI"""
        try:
            # 语音参数
            self.speed_slider.setValue(self.config.get('voice_speed', 100))
            self.volume_slider.setValue(self.config.get('voice_volume', 80))
            
            # 中文发音人设置
            voice_type_cn = self.config.get('voice_type_cn', 'xiaoyan')
            cn_items = [self.voice_combo_cn.itemText(i) for i in range(self.voice_combo_cn.count())]
            cn_match = None
            for item in cn_items:
                if voice_type_cn in item:
                    cn_match = item
                    break
            if cn_match:
                self.voice_combo_cn.setCurrentText(cn_match)
            
            # 英文发音人设置
            voice_type_en = self.config.get('voice_type_en', 'x4_EnUs_Laura_education')
            en_items = [self.voice_combo_en.itemText(i) for i in range(self.voice_combo_en.count())]
            en_match = None
            for item in en_items:
                if voice_type_en in item:
                    en_match = item
                    break
            if en_match:
                self.voice_combo_en.setCurrentText(en_match)
            
            # 根据当前转换类型设置发音人显示
            self.updateVoiceTypeUI()
            
        except Exception as e:
            print(f"加载UI配置失败: {e}")
    
    def onConfigUpdated(self):
        """配置更新回调"""
        self.loadConfig()
        self.loadConfigToUI()
    
    def setupUi(self):
        """设置用户界面"""
        self.setWindowTitle("智能视频语音转换系统 v1.0")
        self.setMinimumSize(920, 680)  # 减小最小高度
        self.resize(920, 680)  # 减小默认高度
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 使用单栏布局，优化空间分配
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(4)  # 进一步减小整体间距
        main_layout.setContentsMargins(8, 8, 8, 8)  # 减小边距
        
        # 添加各个功能区域，并在每个区域间添加分隔线
        # 使用拉伸因子来控制空间分配
        main_layout.addWidget(self.createTitleSection(), 0)  # 固定大小
        main_layout.addWidget(self.createSeparator(), 0)
        main_layout.addWidget(self.createFileSection(), 0)  # 固定大小
        main_layout.addWidget(self.createSeparator(), 0)
        main_layout.addWidget(self.createConversionSection(), 0)  # 固定大小
        main_layout.addWidget(self.createSeparator(), 0)
        main_layout.addWidget(self.createProgressSection(), 0)  # 固定大小
        main_layout.addWidget(self.createSeparator(), 0)
        main_layout.addWidget(self.createButtonSection(), 0)  # 固定大小
        # 缩小处理结果部分和按钮行的间隔
        main_layout.addSpacing(1)  # 进一步减小间距
        main_layout.addWidget(self.createResultSection(), 1)  # 允许拉伸，占用剩余空间
        
        # 创建菜单栏和状态栏
        self.createMenuBar()
        self.createStatusBar()
        
        # 应用样式
        self.applyStyles()
    
    def centerWindow(self):
        """居中显示窗口"""
        screen = QApplication.desktop().screenGeometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def createSeparator(self):
        """创建分隔线"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedHeight(1)
        separator.setStyleSheet("""
            QFrame {
                color: #d0d0d0;
                background-color: #d0d0d0;
                margin: 2px 0px;
            }
        """)
        return separator
    
    def createTitleSection(self):
        """创建标题区域"""
        title_frame = QFrame()
        title_frame.setFixedHeight(45)  # 减小标题区域高度
        
        layout = QVBoxLayout(title_frame)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(2)  # 减小标题间距
        layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        
        # 主标题
        title_label = QLabel("智能视频语音转换系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")  # 稍微减小字体
        
        # 副标题
        subtitle_label = QLabel("专注核心功能演示")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 11px; color: #666;")  # 减小副标题字体
        
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        
        return title_frame
    
    def createFileSection(self):
        """创建文件选择区域"""
        file_frame = QFrame()
        file_frame.setMinimumHeight(70)  # 减小文件区域高度
        
        layout = QVBoxLayout(file_frame)
        layout.setSpacing(4)  # 减小间距
        layout.setContentsMargins(5, 3, 5, 3)  # 减小上下边距
        
        # 标题
        title_label = QLabel("文件选择")
        
        # 视频文件选择
        self.video_input = FileInputWidget("拖拽视频文件至此，或点击浏览")
        self.video_input.pathChanged.connect(self.onVideoPathChanged)
        
        # 输出目录选择
        output_layout = QHBoxLayout()
        output_layout.setSpacing(10)
        self.output_label = QLabel("输出目录: 未选择")
        self.output_label.setMinimumHeight(25)
        
        output_btn = QPushButton("选择输出目录")
        output_btn.clicked.connect(self.selectOutputDir)
        
        output_layout.addWidget(self.output_label, 1)
        output_layout.addWidget(output_btn)
        
        layout.addWidget(title_label)
        layout.addWidget(self.video_input)
        layout.addLayout(output_layout)
        
        return file_frame
    
    def createConversionSection(self):
        """创建转换设置区域"""
        conversion_frame = QFrame()
        conversion_frame.setMinimumHeight(110)  # 增加高度以适应两行发音人选择
        
        layout = QVBoxLayout(conversion_frame)
        layout.setSpacing(4)  # 减小间距
        layout.setContentsMargins(5, 3, 5, 3)  # 减小上下边距
        
        # 标题
        title_label = QLabel("转换设置")
        
        # 转换类型选择
        type_layout = QHBoxLayout()
        type_layout.setSpacing(10)
        type_label = QLabel("转换类型:")
        type_label.setFixedWidth(80)
        
        self.conversion_type = QComboBox()
        self.conversion_type.addItems([
            "智能转换",
            "英文转中文",
            "中文转英文", 
            "英文转英文",
            "中文转中文"
        ])
        self.conversion_type.currentTextChanged.connect(self.updateVoiceTypeUI)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.conversion_type, 1)
        
        # 中文发音人选择
        voice_cn_layout = QHBoxLayout()
        voice_cn_layout.setSpacing(10)
        voice_cn_label = QLabel("中文发音人:")
        voice_cn_label.setFixedWidth(80)
        
        self.voice_combo_cn = QComboBox()
        self.voice_combo_cn.addItems([
            "xiaoyan (女声·亲和)",
            "aisjiuxu (男声·专业)", 
            "aisxping (男声·成熟)",
            "aisjinger (女声·温暖)",
            "aisbabyxu (童声·可爱)"
        ])
        
        voice_cn_layout.addWidget(voice_cn_label)
        voice_cn_layout.addWidget(self.voice_combo_cn, 1)
        
        # 英文发音人选择
        voice_en_layout = QHBoxLayout()
        voice_en_layout.setSpacing(10)
        voice_en_label = QLabel("英文发音人:")
        voice_en_label.setFixedWidth(80)
        
        self.voice_combo_en = QComboBox()
        self.voice_combo_en.addItems([
            "x4_EnUs_Laura_education (女声·教育)",
            "x4_EnUs_Alex_education (男声·教育)",
            "x4_EnUs_Emma_formal (女声·正式)",
            "x4_EnUs_Chris_formal (男声·正式)"
        ])
        
        voice_en_layout.addWidget(voice_en_label)
        voice_en_layout.addWidget(self.voice_combo_en, 1)
        
        # 语音参数设置
        params_layout = QGridLayout()
        params_layout.setHorizontalSpacing(15)
        params_layout.setVerticalSpacing(8)
        params_layout.setContentsMargins(0, 2, 0, 2)
        
        # 语音速度 - 使用EnhancedSlider显示具体数值
        speed_label = QLabel("语音速度:")
        speed_label.setFixedWidth(80)
        self.speed_slider = EnhancedSlider(50, 200, 100, 5, "%")
        params_layout.addWidget(speed_label, 0, 0)
        params_layout.addWidget(self.speed_slider, 0, 1)
        
        # 语音音量 - 使用EnhancedSlider显示具体数值
        volume_label = QLabel("语音音量:")
        volume_label.setFixedWidth(80)
        self.volume_slider = EnhancedSlider(0, 100, 80, 5, "%")
        params_layout.addWidget(volume_label, 1, 0)
        params_layout.addWidget(self.volume_slider, 1, 1)
        
        layout.addWidget(title_label)
        layout.addLayout(type_layout)
        layout.addLayout(voice_cn_layout)
        layout.addLayout(voice_en_layout)
        layout.addLayout(params_layout)
        
        return conversion_frame
    
    def createProgressSection(self):
        """创建进度显示区域"""
        progress_frame = QFrame()
        progress_frame.setMinimumHeight(50)  # 减小进度区域高度
        
        layout = QVBoxLayout(progress_frame)
        layout.setSpacing(3)  # 减小间距
        layout.setContentsMargins(5, 3, 5, 3)  # 减小上下边距
        
        # 标题
        title_label = QLabel("处理进度")
        
        # 进度条
        self.progress_bar = QProgressBar()
        
        # 状态文本
        self.progress_text = QLabel("等待开始...")
        
        layout.addWidget(title_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_text)
        
        return progress_frame
    
    def createButtonSection(self):
        """创建按钮区域"""
        button_frame = QFrame()
        button_frame.setFixedHeight(35)  # 固定按钮区域高度，更紧凑
        
        layout = QHBoxLayout(button_frame)
        layout.setSpacing(6)  # 减小按钮间距
        layout.setContentsMargins(5, 2, 5, 2)  # 减小上下边距
        
        # 开始处理按钮
        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self.startProcessing)
        
        # 暂停/恢复按钮
        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self.toggleProcessing)
        self.pause_btn.setEnabled(False)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stopProcessing)
        self.stop_btn.setEnabled(False)
        
        # 设置按钮
        settings_btn = QPushButton("设置")
        settings_btn.clicked.connect(self.openSettings)
        
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        layout.addWidget(settings_btn)
        
        return button_frame
    
    def createResultSection(self):
        """创建结果显示区域"""
        result_frame = QFrame()
        result_frame.setMinimumHeight(80)  # 减小最小高度
        
        layout = QVBoxLayout(result_frame)
        layout.setSpacing(4)  # 减小间距
        layout.setContentsMargins(5, 3, 5, 5)  # 减小上边距，保持下边距
        
        # 标题
        title_label = QLabel("处理结果")
        title_label.setStyleSheet("font-weight: bold; margin-bottom: 2px;")
        
        # 结果显示区域 - 改为自适应高度
        self.result_text = QTextEdit()
        self.result_text.setMinimumHeight(60)  # 设置最小高度而不是固定高度
        self.result_text.setReadOnly(True)
        # 设置合适的大小策略，让它能够扩展
        self.result_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 初始化结果文本
        self.result_text.setText("功能演示\n支持多种语言转换：智能转换、英转中、中转英、英转英、中转中\n✨ 智能转换：自动检测视频语言并选择最佳转换方式\n🎯 智能语音识别和高质量语音合成\n📱 选择视频文件并设置输出目录，点击开始处理即可体验！")
        
        # 操作按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # 减小按钮间距
        button_layout.setContentsMargins(0, 2, 0, 0)  # 减小上边距
        
        # 打开结果文件夹按钮
        self.open_folder_btn = QPushButton("打开结果文件夹")
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.setFixedHeight(28)  # 设置按钮高度
        self.open_folder_btn.clicked.connect(self.openResultFolder)
        
        button_layout.addStretch()
        button_layout.addWidget(self.open_folder_btn)
        
        layout.addWidget(title_label)
        layout.addWidget(self.result_text, 1)  # 让结果文本区域占用大部分空间
        layout.addLayout(button_layout)
        
        return result_frame

    def updateVoiceTypeUI(self):
        """更新发音人选择显示"""
        selected_type = self.conversion_type.currentText()
        
        # 获取布局中的发音人控件
        voice_cn_widgets = [self.voice_combo_cn.parent().layout().itemAt(i).widget() 
                           for i in range(self.voice_combo_cn.parent().layout().count())]
        voice_en_widgets = [self.voice_combo_en.parent().layout().itemAt(i).widget() 
                           for i in range(self.voice_combo_en.parent().layout().count())]
        
        if selected_type == "智能转换":
            # 智能转换：显示中英文发音人
            for widget in voice_cn_widgets:
                if widget:
                    widget.setVisible(True)
            for widget in voice_en_widgets:
                if widget:
                    widget.setVisible(True)
        elif selected_type in ["中文转英文", "英文转英文"]:
            # 输出英文：只显示英文发音人
            for widget in voice_cn_widgets:
                if widget:
                    widget.setVisible(False)
            for widget in voice_en_widgets:
                if widget:
                    widget.setVisible(True)
        else:  # 中文转中文, 英文转中文
            # 输出中文：只显示中文发音人
            for widget in voice_cn_widgets:
                if widget:
                    widget.setVisible(True)
            for widget in voice_en_widgets:
                if widget:
                    widget.setVisible(False)

    def startProcessing(self):
        """开始处理"""
        # 验证输入
        if not self.video_input.file_path:
            QMessageBox.warning(self, "警告", "请先选择视频文件！")
            return
        
        if "未选择" in self.output_label.text():
            QMessageBox.warning(self, "警告", "请先选择输出目录！")
            return

        self.is_processing = True
        self.is_paused = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(False)
        
        # 获取当前配置
        current_config = self.config.copy()
        
        # 获取发音人选择
        voice_type_cn = self.voice_combo_cn.currentText().split(' (')[0]  # 提取实际的voice名称
        voice_type_en = self.voice_combo_en.currentText().split(' (')[0]  # 提取实际的voice名称
        
        # 根据转换类型决定使用哪个发音人
        conversion_type = self.conversion_type.currentText()
        if conversion_type == "智能转换":
            voice_type = "auto_detect"  # 智能转换的特殊标记
        elif conversion_type in ["中文转英文", "英文转英文"]:
            voice_type = voice_type_en
        else:  # 中文转中文, 英文转中文
            voice_type = voice_type_cn
        
        current_config.update({
            'voice_speed': self.speed_slider.value(),
            'voice_volume': self.volume_slider.value(),
            'voice_type': voice_type,
            'voice_type_cn': voice_type_cn,
            'voice_type_en': voice_type_en
        })
        
        # 提取输出目录路径
        output_dir = self.output_label.text().replace("输出目录: ", "")
        
        self.process_thread = MiddleProcessThread(
            self.video_input.file_path, 
            output_dir, 
            self.conversion_type.currentText(), 
            current_config
        )
        self.process_thread.progress.connect(self.updateProgress)
        self.process_thread.finished.connect(self.handleProcessingFinished)
        self.process_thread.start()

    def toggleProcessing(self):
        """暂停或恢复处理"""
        if self.process_thread and not self.is_paused:
            self.is_paused = True
            self.pause_btn.setText("恢复")
            self.process_thread.pause()
        elif self.process_thread and self.is_paused:
            self.is_paused = False
            self.pause_btn.setText("暂停")
            self.process_thread.resume()

    def stopProcessing(self):
        """停止处理"""
        if self.process_thread:
            self.process_thread.stop()
        
        self.is_processing = False
        self.is_paused = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_text.setText("处理已停止")

    def updateProgress(self, progress, message):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.progress_text.setText(message)

    def handleProcessingFinished(self, success, result):
        """处理完成后的回调"""
        self.is_processing = False
        self.is_paused = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("暂停")
        self.stop_btn.setEnabled(False)
        
        if success:
            self.result_text.setHtml(f"""
            <div style='color: #22543d; padding: 15px;'>
                <p><strong>✅ 处理成功完成！</strong></p>
                <p style='margin-top: 10px;'>{result}</p>
                <p style='margin-top: 10px; font-size: 11px; color: #666;'>
                    点击下方按钮打开结果文件夹查看输出文件
                </p>
            </div>
            """)
            self.open_folder_btn.setEnabled(True)
        else:
            self.result_text.setHtml(f"""
            <div style='color: #c53030; padding: 15px;'>
                <p><strong>❌ 处理失败</strong></p>
                <p style='margin-top: 10px;'>{result}</p>
                <p style='margin-top: 10px; font-size: 11px; color: #666;'>
                    请检查输入文件和设置后重试
                </p>
            </div>
            """)

    def openResultFolder(self):
        """打开结果文件夹"""
        output_dir = self.output_label.text().replace("输出目录: ", "")
        if output_dir and output_dir != "未选择":
            try:
                if sys.platform.startswith('win'):
                    os.startfile(output_dir)
                elif sys.platform.startswith('darwin'):
                    os.system(f'open "{output_dir}"')
                else:
                    os.system(f'xdg-open "{output_dir}"')
            except Exception as e:
                QMessageBox.warning(self, "错误", f"打开结果文件夹失败: {e}")

    def openSettings(self):
        """打开设置对话框"""
        dialog = MiddleSettingsDialog(self)
        dialog.configUpdated.connect(self.onConfigUpdated)
        dialog.exec_()

    def applyStyles(self):
        """应用样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f4f8;
            }
        """)

    def createMenuBar(self):
        """创建菜单栏"""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction("退出", self.close)
        
        help_menu = menu_bar.addMenu("帮助")
        help_menu.addAction("关于", self.showAbout)

    def createStatusBar(self):
        """创建状态栏"""
        self.statusBar().showMessage(" 准备就绪")

    def showAbout(self):
        """显示关于对话框"""
        about_text = """
        <h3>智能视频语音转换系统</h3>
        <p><b>本:</b> v1.0</p>
        <br>
        <p><b>主要功能:</b></p>
        <ul>
        <li>🎬 智能视频语音识别转换</li>
        <li>🎤 多语言语音合成 (中文/英文)</li>
        <li>🔄 支持多种转换模式</li>
        <li>⚡ 优化的处理流程</li>
        </ul>
        <br>
        <p><b>技术特点:</b></p>
        <ul>
        <li>科大讯飞语音识别API</li>
        <li>科大讯飞语音合成API</li>
        <li>百度翻译API</li>
        <li>现代化PyQt5界面</li>
        </ul>
        <br>
        <p style='color: #666; font-size: 12px;'>
        本本专为优化，专注展示核心功能
        </p>
        """
        
        QMessageBox.about(self, "关于", about_text)

    def onVideoPathChanged(self, path):
        """视频路径变化时的回调"""
        self.output_label.setText(f"输出目录: {os.path.dirname(path)}")

    def selectOutputDir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_label.setText(f"输出目录: {dir_path}")

# --- main函数 ---
def main():
    """主函数"""
    # 设置控制台编码为UTF-8，修复乱码问题
    if sys.platform.startswith('win'):
        try:
            import locale
            locale.setlocale(locale.LC_ALL, 'Chinese')
        except Exception as e:
            print(f"设置中文locale失败: {e}")
    
    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("智能视频语音转换系统")
    app.setApplicationVersion("1.0")
    
    # 设置应用程序图标
    try:
        app.setWindowIcon(app_icon.get_app_icon())
    except Exception as e:
        print(f"设置应用图标失败: {e}")
    
    # 创建并显示主窗口
    window = MiddleMainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()