# -*- coding: utf-8 -*-
"""
批量处理模块 v3.1 (增强版)
支持批量处理多个视频文件
- 新增智能转换功能
- 支持语音参数配置
- 完善错误处理和进度显示
- 增强滑块组件支持
- 图标和色彩优化
"""

import os
import sys
import json
import threading
import re
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# 导入处理模块
import addNewSound
import addSrt
import video_to_txt
import voice_get_text
import syntheticSpeech
import syntheticSpeechCn
import syntheticSpeechTranslateToEn
import syntheticSpeechTranslateToCn
import generateWav

# --- 增强滑块组件 (从enhanced_UI.py复制) ---
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

class BatchProcessThread(QThread):
    """批量处理线程"""
    progress = pyqtSignal(int)
    current_file = pyqtSignal(str)
    file_completed = pyqtSignal(str, bool, str)
    all_completed = pyqtSignal()
    
    def __init__(self, file_list, output_dir, file_configs=None, global_config=None):
        super().__init__()
        self.file_list = file_list
        self.output_dir = output_dir
        self.file_configs = file_configs or {}  # 单独配置字典
        self.global_config = global_config  # 统一配置
        self.is_running = True
        
    def detectLanguage(self, text):
        """检测文本语言（简化版）"""
        if not text:
            return "unknown"
        
        # 检测中文字符
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len(text.replace(' ', '').replace('\n', ''))
        
        if total_chars == 0:
            return "unknown"
        
        chinese_ratio = chinese_chars / total_chars
        return "chinese" if chinese_ratio > 0.3 else "english"
        
    def run(self):
        try:
            total_files = len(self.file_list)
            completed_files = 0
        
            for i, video_file in enumerate(self.file_list):
                if not self.is_running:
                    break
                
                # 获取该文件的配置
                if video_file in self.file_configs:
                    config = self.file_configs[video_file]
                    conversion_type = config['conversion_type']
                    voice_params = {
                        'voice_type': config['voice_type'],
                        'speed': config['speed'],
                        'volume': config['volume'],
                        'quality': config['quality']
                    }
                else:
                    # 使用全局配置
                    conversion_type = self.global_config['conversion_type']
                    voice_params = {
                        'voice_type': self.global_config['voice_type'],
                        'speed': self.global_config['speed'],
                        'volume': self.global_config['volume'],
                        'quality': self.global_config['quality']
                    }
                
                self.current_file.emit(f"正在处理: {os.path.basename(video_file)} ({conversion_type})")
                
                try:
                    success, message = self.process_single_file(video_file, self.output_dir, conversion_type, voice_params)
                    self.file_completed.emit(video_file, success, message)
                    
                    if success:
                        completed_files += 1
                
                except Exception as e:
                    error_msg = f"处理文件时发生错误: {str(e)}"
                    self.file_completed.emit(video_file, False, error_msg)
            
                # 更新总进度
                progress = int((i + 1) / total_files * 100)
                self.progress.emit(progress)
        
            self.all_completed.emit()
    
        except Exception as e:
            print(f"批处理线程错误: {e}")
            import traceback
            traceback.print_exc()

    def process_single_file(self, video_file, output_dir, conversion_type, voice_params):
        """处理单个文件，支持单独配置"""
        try:
            if not self.is_running:
                return False, "处理已停止"
            
            print(f"开始处理文件: {video_file}")
            print(f"转换类型: {conversion_type}")
            print(f"语音参数: {voice_params}")
            
            # 创建文件专用的输出目录
            base_name = os.path.splitext(os.path.basename(video_file))[0]
            file_output_dir = os.path.join(output_dir, base_name)
            os.makedirs(file_output_dir, exist_ok=True)
            
            # 1. 提取音频
            import generateWav
            wav_path = generateWav.run(video_file, file_output_dir)
            if not os.path.exists(wav_path):
                return False, "音频提取失败"
            
            # 2. 生成无声视频
            import addNewSound
            video_without_sound = addNewSound.del_audio(video_file, file_output_dir)
            if not os.path.exists(video_without_sound):
                return False, "无声视频生成失败"
            
            # 3. 语音识别
            import video_to_txt
            video_to_txt.run(wav_path, file_output_dir)
            
            subtitle_file = os.path.join(file_output_dir, "subtitle.srt")
            if not os.path.exists(subtitle_file):
                return False, "语音识别失败"
            
            # 智能转换逻辑
            actual_conversion_type = conversion_type
            if conversion_type == "智能转换":
                # 检测语言
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                detected_lang = self.detectLanguage(content)
                
                if detected_lang == "chinese":
                    actual_conversion_type = "中文转英文"
                elif detected_lang == "english":
                    actual_conversion_type = "英文转中文"
                else:
                    actual_conversion_type = "英文转中文"  # 默认
            
            # 4. 语音合成
            type_map = {
                "智能转换": "smart",
                "中文转英文": "cn_to_en", 
                "中文转中文": "cn_to_cn", 
                "英文转中文": "en_to_cn", 
                "英文转英文": "en_to_en"
            }
            conversion_suffix = type_map.get(actual_conversion_type, 'new')
            
            name, ext = os.path.splitext(base_name)
            final_video_path = os.path.join(file_output_dir, f"{name}_{conversion_suffix}{ext}")
            
            # 获取语音参数
            voice_type = voice_params.get('voice_type', 'xiaoyan')
            speed = voice_params.get('speed', 100)
            volume = voice_params.get('volume', 80)
            
            # 根据转换类型调用相应的合成函数
            generated_video_path = None
            try:
                if actual_conversion_type == "中文转英文":
                    import syntheticSpeechTranslateToEn
                    generated_video_path = syntheticSpeechTranslateToEn.run(
                        video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume
                    )
                elif actual_conversion_type == "中文转中文":
                    import syntheticSpeechCn
                    generated_video_path = syntheticSpeechCn.run(
                        video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume
                    )
                elif actual_conversion_type == "英文转中文":
                    import syntheticSpeechTranslateToCn
                    generated_video_path = syntheticSpeechTranslateToCn.run(
                        video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume
                    )
                elif actual_conversion_type == "英文转英文":
                    import syntheticSpeech
                    generated_video_path = syntheticSpeech.run(
                        video_without_sound, subtitle_file, final_video_path, voice_type, speed, volume
                    )
            except Exception as e:
                return False, f"语音合成失败: {str(e)}"
            
            # 验证输出文件
            final_output = generated_video_path if generated_video_path and os.path.exists(generated_video_path) else final_video_path
            
            if os.path.exists(final_output):
                file_size = os.path.getsize(final_output) / (1024 * 1024)
                success_msg = f"处理成功 ({actual_conversion_type}) - {file_size:.1f}MB"
                print(f"✅ {success_msg}: {final_output}")
                return True, success_msg
            else:
                return False, f"输出文件未生成: {final_output}"
                
        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return False, error_msg

    def embedSubtitles(self, video_file, subtitle_file):
        """嵌入字幕到视频（简化版）"""
        # 这个方法保持原样，用于向后兼容
        return True
    
    def stop_processing(self):
        """停止处理"""
        self.is_running = False

class BatchProcessDialog(QDialog):
    """批量处理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_list = []
        self.output_dir = ""
        self.process_thread = None
        
        # 新增：文件配置字典，存储每个文件的单独配置
        self.file_configs = {}  # {file_path: {'conversion_type': str, 'voice_params': dict}}
        
        self.setupUi()
        
    def setupUi(self):
        self.setWindowTitle("批量视频处理")
        self.setModal(True)
        self.resize(1100, 800)  # 增加窗口大小以确保组件完整显示
        
        layout = QVBoxLayout(self)
        layout.setSpacing(18)  # 增加间距
        layout.setContentsMargins(25, 25, 25, 25)  # 增加边距确保显示完整
        
        # 顶部标题
        title_label = QLabel("批量视频语音转换处理")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #0078D7;
                padding: 12px;
                background-color: #f0f8ff;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
            }
        """)
        layout.addWidget(title_label)
        
        # 创建主要内容区域的水平布局
        main_content = QHBoxLayout()
        main_content.setSpacing(18)
        
        # 左侧：文件列表区域
        left_panel = QVBoxLayout()
        
        # 文件列表区域
        file_section = QGroupBox("文件列表")
        file_section.setMinimumWidth(480)
        file_section.setMaximumHeight(200)  # 减小文件列表区域高度
        file_layout = QVBoxLayout(file_section)
        file_layout.setSpacing(8)  # 减小组件间距
        file_layout.setContentsMargins(10, 10, 10, 10)  # 减小边距
        
        # 文件操作按钮
        file_buttons_container = QWidget()
        file_buttons_container.setMinimumHeight(60)  # 减小按钮区域高度
        file_buttons_layout = QHBoxLayout(file_buttons_container)
        file_buttons_layout.setSpacing(8)  # 减小按钮间距
        file_buttons_layout.setContentsMargins(5, 5, 5, 5)  # 减小边距
        
        add_files_btn = QPushButton("添加文件")
        add_files_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        add_files_btn.clicked.connect(self.addFiles)
        add_files_btn.setMinimumHeight(32)  # 减小按钮高度
        add_files_btn.setMinimumWidth(70)  # 减小按钮宽度
        
        add_folder_btn = QPushButton("添加文件夹")
        add_folder_btn.setIcon(self.style().standardIcon(QStyle.SP_DirIcon))
        add_folder_btn.clicked.connect(self.addFolder)
        add_folder_btn.setMinimumHeight(32)  # 减小按钮高度
        add_folder_btn.setMinimumWidth(80)  # 调整按钮宽度
        
        remove_btn = QPushButton("移除选中")
        remove_btn.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        remove_btn.clicked.connect(self.removeSelected)
        remove_btn.setMinimumHeight(32)  # 减小按钮高度
        remove_btn.setMinimumWidth(70)  # 减小按钮宽度
        
        clear_btn = QPushButton("清空列表")
        clear_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        clear_btn.clicked.connect(self.clearList)
        clear_btn.setMinimumHeight(32)  # 减小按钮高度
        clear_btn.setMinimumWidth(70)  # 减小按钮宽度
        
        view_config_btn = QPushButton("查看配置")
        view_config_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        view_config_btn.clicked.connect(self.viewAllConfigurations)
        view_config_btn.setMinimumHeight(32)  # 减小按钮高度
        view_config_btn.setMinimumWidth(70)  # 减小按钮宽度
        
        file_buttons_layout.addWidget(add_files_btn)
        file_buttons_layout.addWidget(add_folder_btn)
        file_buttons_layout.addWidget(remove_btn)
        file_buttons_layout.addWidget(clear_btn)
        file_buttons_layout.addWidget(view_config_btn)
        file_buttons_layout.addStretch()
        
        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list_widget.setMinimumHeight(80)  # 减小文件列表高度
        self.file_list_widget.setMaximumHeight(120)  # 减小最大高度
        self.file_list_widget.itemSelectionChanged.connect(self.onFileSelectionChanged)
        
        # 文件数量显示
        self.file_count_label = QLabel("已添加 0 个文件")
        self.file_count_label.setStyleSheet("font-weight: bold; color: #0078D7; margin: 5px;")
        
        file_layout.addWidget(file_buttons_container)
        file_layout.addWidget(self.file_list_widget)
        file_layout.addWidget(self.file_count_label)
        
        left_panel.addWidget(file_section)
        
        # 进度和控制区域
        progress_section = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_section)
        progress_layout.setSpacing(10)
        
        # 总体进度条
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(100)
        self.overall_progress.setValue(0)
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078D7;
                border-radius: 5px;
            }
        """)
        
        # 当前文件进度条
        self.current_file_progress = QProgressBar()
        self.current_file_progress.setMinimum(0)
        self.current_file_progress.setMaximum(100)
        self.current_file_progress.setValue(0)
        self.current_file_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 6px;
                text-align: center;
                font-weight: bold;
                font-size: 11px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 5px;
            }
        """)
        
        # 进度标签
        self.overall_progress_label = QLabel("总体进度: 等待开始...")
        self.overall_progress_label.setStyleSheet("font-weight: bold; color: #333; font-size: 12px;")
        
        self.current_file_label = QLabel("当前文件: 未开始")
        self.current_file_label.setStyleSheet("font-weight: bold; color: #666; font-size: 11px;")
        
        # 处理状态显示
        self.status_label = QLabel("状态: 等待开始处理...")
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #333;
                padding: 8px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
            }
        """)
        
        progress_layout.addWidget(self.overall_progress_label)
        progress_layout.addWidget(self.overall_progress)
        progress_layout.addWidget(self.current_file_label)
        progress_layout.addWidget(self.current_file_progress)
        progress_layout.addWidget(self.status_label)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)
        
        self.start_btn = QPushButton("开始批量处理")
        self.start_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.start_btn.setMinimumHeight(42)  # 增加按钮高度
        self.start_btn.setMinimumWidth(150)  # 增加按钮宽度，确保文字显示完全
        self.start_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #333;
                border-radius: 8px;
                background-color: white;
                color: black;
                padding: 10px 15px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #f8f9fa;
                border-color: #555;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: white;
            }
        """)
        self.start_btn.clicked.connect(self.startBatchProcessing)
        
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_btn.setMinimumHeight(42)  # 增加按钮高度
        self.stop_btn.setMinimumWidth(120)  # 增加按钮宽度
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #dc3545;
                border-radius: 8px;
                background-color: #dc3545;
                color: black;
                padding: 10px 15px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #c82333;
                border-color: #c82333;
                color: black;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                border-color: #6c757d;
                color: white;
            }
        """)
        self.stop_btn.clicked.connect(self.stopBatchProcessing)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()  # 弹性空间
        
        progress_layout.addLayout(control_layout)
        
        left_panel.addWidget(progress_section)
        
        # 输出目录选择
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout(output_group)
        output_layout.setSpacing(8)
        
        output_dir_layout = QHBoxLayout()
        output_dir_layout.setSpacing(10)
        
        self.output_path_label = QLabel("未选择输出目录")
        self.output_path_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #f8f9fa;
                font-size: 11px;
                color: #666;
            }
        """)
        
        self.output_dir_btn = QPushButton("选择输出目录")
        self.output_dir_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.output_dir_btn.setMinimumHeight(32)
        self.output_dir_btn.clicked.connect(self.selectOutputDir)
        
        output_dir_layout.addWidget(self.output_path_label, 1)
        output_dir_layout.addWidget(self.output_dir_btn, 0)
        
        output_layout.addLayout(output_dir_layout)
        
        left_panel.addWidget(output_group)
        
        # 日志显示区域
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(5)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)
        self.log_text.setMinimumHeight(80)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 6px;
                background-color: #fafafa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                padding: 5px;
            }
        """)
        
        # 日志控制按钮
        log_control_layout = QHBoxLayout()
        
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.setIcon(self.style().standardIcon(QStyle.SP_DialogResetButton))
        clear_log_btn.setMaximumWidth(80)
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        
        log_control_layout.addStretch()
        log_control_layout.addWidget(clear_log_btn)
        
        log_layout.addWidget(self.log_text)
        log_layout.addLayout(log_control_layout)
        
        left_panel.addWidget(log_group)
        
        # 右侧区域：配置面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 配置模式选择 - 左对齐
        config_mode_group = QGroupBox("配置模式")
        config_mode_layout = QVBoxLayout(config_mode_group)
        config_mode_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 左对齐
        
        self.global_config_radio = QRadioButton("统一配置（所有文件使用相同设置）")
        self.global_config_radio.setStyleSheet("QRadioButton { text-align: left; }")  # 文字左对齐
        self.individual_config_radio = QRadioButton("单独配置（每个文件使用不同设置）")
        self.individual_config_radio.setStyleSheet("QRadioButton { text-align: left; }")  # 文字左对齐
        self.global_config_radio.setChecked(True)  # 默认统一配置
        
        # 配置模式改变时的处理
        self.global_config_radio.toggled.connect(self.onConfigModeChanged)
        self.individual_config_radio.toggled.connect(self.onConfigModeChanged)
        
        config_mode_layout.addWidget(self.global_config_radio, 0, Qt.AlignLeft)
        config_mode_layout.addWidget(self.individual_config_radio, 0, Qt.AlignLeft)
        
        # 配置面板容器
        self.config_container = QWidget()
        config_container_layout = QVBoxLayout(self.config_container)
        
        # 文件选择提示（仅在单独配置模式下显示）
        self.file_selection_label = QLabel("请在左侧选择一个文件以配置其参数")
        self.file_selection_label.setAlignment(Qt.AlignCenter)
        self.file_selection_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-style: italic;
                padding: 20px;
                border: 2px dashed #ccc;
                border-radius: 8px;
                background-color: #f9f9f9;
            }
        """)
        self.file_selection_label.setVisible(False)
        
        # 当前配置的文件名显示（仅在单独配置模式下显示）
        self.current_config_file_label = QLabel()
        self.current_config_file_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #0078D7;
                padding: 8px;
                background-color: #e7f3ff;
                border-radius: 4px;
                border: 1px solid #0078D7;
            }
        """)
        self.current_config_file_label.setVisible(False)
        
        # 转换配置区域 - 左对齐
        conversion_group = QGroupBox("转换设置")
        conversion_layout = QGridLayout(conversion_group)
        conversion_layout.setSpacing(10)
        conversion_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 左对齐
        
        # 转换类型
        conversion_type_label = QLabel("转换类型:")
        conversion_type_label.setStyleSheet("font-weight: bold; color: #333;")
        conversion_type_label.setAlignment(Qt.AlignLeft)  # 标签左对齐
        self.conversion_combo = QComboBox()
        self.conversion_combo.addItems([
            "智能转换", "中文转英文", "中文转中文", "英文转中文", "英文转英文"
        ])
        self.conversion_combo.currentTextChanged.connect(self.onConfigChanged)
        
        # 发音人
        voice_label = QLabel("发音人:")
        voice_label.setStyleSheet("font-weight: bold; color: #333;")
        voice_label.setAlignment(Qt.AlignLeft)  # 标签左对齐
        self.voice_combo = QComboBox()
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
        self.voice_combo.currentTextChanged.connect(self.onConfigChanged)
        
        conversion_layout.addWidget(conversion_type_label, 0, 0, Qt.AlignLeft)
        conversion_layout.addWidget(self.conversion_combo, 0, 1, Qt.AlignLeft)
        conversion_layout.addWidget(voice_label, 1, 0, Qt.AlignLeft)
        conversion_layout.addWidget(self.voice_combo, 1, 1, Qt.AlignLeft)
        
        # 语音参数区域 - 左对齐
        voice_params_group = QGroupBox("语音参数")
        voice_params_layout = QGridLayout(voice_params_group)
        voice_params_layout.setSpacing(10)
        voice_params_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # 左对齐
        
        # 语速
        speed_label = QLabel("语速:")
        speed_label.setStyleSheet("font-weight: bold; color: #333;")
        speed_label.setAlignment(Qt.AlignLeft)  # 标签左对齐
        self.speed_slider = EnhancedSlider(50, 200, 100, 5, "%")
        self.speed_slider.valueChanged.connect(self.onConfigChanged)
        
        # 音量
        volume_label = QLabel("音量:")
        volume_label.setStyleSheet("font-weight: bold; color: #333;")
        volume_label.setAlignment(Qt.AlignLeft)  # 标签左对齐
        self.volume_slider = EnhancedSlider(0, 100, 80, 5, "%")
        self.volume_slider.valueChanged.connect(self.onConfigChanged)
        
        # 质量
        quality_label = QLabel("输出质量:")
        quality_label.setStyleSheet("font-weight: bold; color: #333;")
        quality_label.setAlignment(Qt.AlignLeft)  # 标签左对齐
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["标准质量", "高质量", "超清质量"])
        self.quality_combo.setCurrentIndex(1)  # 默认高质量
        self.quality_combo.currentTextChanged.connect(self.onConfigChanged)
        
        voice_params_layout.addWidget(speed_label, 0, 0, Qt.AlignLeft)
        voice_params_layout.addWidget(self.speed_slider, 0, 1, Qt.AlignLeft)
        voice_params_layout.addWidget(volume_label, 1, 0, Qt.AlignLeft)
        voice_params_layout.addWidget(self.volume_slider, 1, 1, Qt.AlignLeft)
        voice_params_layout.addWidget(quality_label, 2, 0, Qt.AlignLeft)
        voice_params_layout.addWidget(self.quality_combo, 2, 1, Qt.AlignLeft)
        
        # 配置操作按钮
        config_buttons_layout = QHBoxLayout()
        
        self.apply_to_all_btn = QPushButton("应用到所有文件")
        self.apply_to_all_btn.setToolTip("将当前配置应用到所有文件")
        self.apply_to_all_btn.clicked.connect(self.applyConfigToAll)
        self.apply_to_all_btn.setVisible(False)  # 仅在单独配置模式下显示
        
        self.reset_config_btn = QPushButton("重置为默认")
        self.reset_config_btn.setToolTip("重置当前配置为默认值")
        self.reset_config_btn.clicked.connect(self.resetCurrentConfig)
        
        config_buttons_layout.addWidget(self.apply_to_all_btn)
        config_buttons_layout.addWidget(self.reset_config_btn)
        config_buttons_layout.addStretch()
        
        # 字幕显示区域
        subtitle_group = QGroupBox("字幕预览")
        subtitle_layout = QVBoxLayout(subtitle_group)
        subtitle_layout.setSpacing(8)
        
        # 文件选择器
        subtitle_file_layout = QHBoxLayout()
        subtitle_file_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        
        subtitle_file_label = QLabel("查看文件:")
        subtitle_file_label.setStyleSheet("font-weight: bold; color: #333;")
        subtitle_file_label.setAlignment(Qt.AlignLeft)
        
        self.subtitle_file_combo = QComboBox()
        self.subtitle_file_combo.addItem("请先添加文件...")
        self.subtitle_file_combo.setMinimumWidth(200)
        self.subtitle_file_combo.currentTextChanged.connect(self.onSubtitleFileChanged)
        
        subtitle_file_layout.addWidget(subtitle_file_label)
        subtitle_file_layout.addWidget(self.subtitle_file_combo)
        subtitle_file_layout.addStretch()
        
        # 字幕标签页
        self.subtitle_tabs = QTabWidget()
        self.subtitle_tabs.setMaximumHeight(200)  # 限制高度
        
        # 原始字幕页
        original_subtitle_widget = QWidget()
        original_subtitle_layout = QVBoxLayout(original_subtitle_widget)
        original_subtitle_layout.setContentsMargins(5, 5, 5, 5)
        
        self.original_subtitle_text = QTextEdit()
        self.original_subtitle_text.setPlaceholderText("原始字幕将在处理时显示...")
        self.original_subtitle_text.setReadOnly(True)
        self.original_subtitle_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                padding: 5px;
            }
        """)
        
        original_subtitle_layout.addWidget(self.original_subtitle_text)
        self.subtitle_tabs.addTab(original_subtitle_widget, "原始字幕")
        
        # 转换后字幕页
        converted_subtitle_widget = QWidget()
        converted_subtitle_layout = QVBoxLayout(converted_subtitle_widget)
        converted_subtitle_layout.setContentsMargins(5, 5, 5, 5)
        
        self.converted_subtitle_text = QTextEdit()
        self.converted_subtitle_text.setPlaceholderText("转换后字幕将在处理完成后显示...")
        self.converted_subtitle_text.setReadOnly(True)
        self.converted_subtitle_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fafafa;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
                padding: 5px;
            }
        """)
        
        converted_subtitle_layout.addWidget(self.converted_subtitle_text)
        self.subtitle_tabs.addTab(converted_subtitle_widget, "转换后字幕")
        
        # 字幕操作按钮
        subtitle_buttons_layout = QHBoxLayout()
        subtitle_buttons_layout.setAlignment(Qt.AlignLeft)  # 左对齐
        
        self.clear_subtitles_btn = QPushButton("清空字幕")
        self.clear_subtitles_btn.setMaximumWidth(80)
        self.clear_subtitles_btn.clicked.connect(self.clearSubtitles)
        
        self.export_subtitle_btn = QPushButton("导出字幕")
        self.export_subtitle_btn.setMaximumWidth(80)
        self.export_subtitle_btn.clicked.connect(self.exportCurrentSubtitle)
        self.export_subtitle_btn.setEnabled(False)
        
        subtitle_buttons_layout.addWidget(self.clear_subtitles_btn)
        subtitle_buttons_layout.addWidget(self.export_subtitle_btn)
        subtitle_buttons_layout.addStretch()
        
        subtitle_layout.addLayout(subtitle_file_layout)
        subtitle_layout.addWidget(self.subtitle_tabs)
        subtitle_layout.addLayout(subtitle_buttons_layout)
        
        # 字幕数据存储
        self.subtitle_data = {}  # 存储每个文件的字幕数据 {file_path: {'original': str, 'converted': str}}
        
        # 组装配置面板
        config_container_layout.addWidget(self.file_selection_label)
        config_container_layout.addWidget(self.current_config_file_label)
        config_container_layout.addWidget(conversion_group)
        config_container_layout.addWidget(voice_params_group)
        config_container_layout.addLayout(config_buttons_layout)
        config_container_layout.addWidget(subtitle_group)
        config_container_layout.addStretch()
        
        right_layout.addWidget(config_mode_group)
        right_layout.addWidget(self.config_container)
        
        # 组装主布局
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        
        main_content.addWidget(left_widget)
        main_content.addWidget(right_widget, 1)  # 右侧占更多空间
        layout.addLayout(main_content)
    
    def addFiles(self):
        """添加文件"""
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择视频文件", "",
                "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*)"
            )
            
            if files:
                added_count = 0
                for file_path in files:
                    # 标准化路径格式，确保重复检查的准确性
                    normalized_path = os.path.normpath(os.path.abspath(file_path)).replace('\\', '/')
                    
                    # 检查是否已存在（使用标准化路径比较）
                    normalized_existing_paths = [os.path.normpath(os.path.abspath(p)).replace('\\', '/') for p in self.file_list]
                    
                    if normalized_path not in normalized_existing_paths:
                        self.file_list.append(file_path)  # 保存原始路径
                        item = QListWidgetItem(os.path.basename(file_path))
                        item.setData(Qt.UserRole, file_path)
                        item.setToolTip(file_path)
                        self.file_list_widget.addItem(item)
                        added_count += 1
                
                # 安全更新UI组件
                    self.updateFileCount()
                self.updateSubtitleFileList()  # 更新字幕文件列表
                if added_count > 0:
                    self.addLog(f"添加了 {added_count} 个视频文件")
                else:
                    self.addLog("所有选择的文件都已存在于列表中")
                    
        except Exception as e:
            print(f"添加文件时出错: {e}")
            try:
                    self.addLog(f"添加文件失败: {str(e)}")
            except:
                pass
    
    def addFolder(self):
        """添加文件夹中的所有视频"""
        try:
            folder_path = QFileDialog.getExistingDirectory(
                self, "选择包含视频文件的文件夹"
            )
            
            if folder_path:
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
                added_count = 0
                skipped_count = 0
                
                # 预先标准化现有文件路径列表
                normalized_existing_paths = [os.path.normpath(os.path.abspath(p)).replace('\\', '/') for p in self.file_list]
                
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in video_extensions):
                            file_path = os.path.join(root, file)
                            # 标准化路径格式
                            normalized_path = os.path.normpath(os.path.abspath(file_path)).replace('\\', '/')
                            
                            # 防止重复添加
                            if normalized_path not in normalized_existing_paths:
                                self.file_list.append(file_path)  # 保存原始路径
                                normalized_existing_paths.append(normalized_path)  # 更新已存在列表
                                item = QListWidgetItem(file)
                                item.setData(Qt.UserRole, file_path)
                                item.setToolTip(file_path)
                                self.file_list_widget.addItem(item)
                                added_count += 1
                            else:
                                skipped_count += 1
                
                # 安全更新UI组件
                    self.updateFileCount()
                self.updateSubtitleFileList()  # 更新字幕文件列表
                log_message = f"从文件夹添加了 {added_count} 个视频文件"
                if skipped_count > 0:
                    log_message += f"，跳过 {skipped_count} 个重复文件"
                self.addLog(log_message)
                
        except Exception as e:
            print(f"添加文件夹时出错: {e}")
            try:
                    self.addLog(f"添加文件夹失败: {str(e)}")
            except:
                pass
    
    def removeSelected(self):
        """移除选中的文件"""
        selected_items = self.file_list_widget.selectedItems()
        for item in selected_items:
            row = self.file_list_widget.row(item)
            self.file_list_widget.takeItem(row)
            if row < len(self.file_list):
                self.file_list.pop(row)
        
        self.updateFileCount()
        self.updateSubtitleFileList()  # 更新字幕文件列表
    
    def clearList(self):
        """清空文件列表"""
        self.file_list_widget.clear()
        self.file_list.clear()
        self.updateFileCount()
        self.updateSubtitleFileList()  # 更新字幕文件列表
    
    def updateFileCount(self):
        """更新文件数量显示"""
        try:
            count = len(self.file_list)
            if hasattr(self, 'file_count_label'):
                self.file_count_label.setText(f"已添加 {count} 个文件")
                print(f"文件数量更新: {count}")
            
            # 更新配置模式显示
            if hasattr(self, 'individual_config_radio') and self.individual_config_radio.isChecked():
                self.updateConfigPanelForIndividual()
                
        except RuntimeError as e:
            # Qt对象已被删除，使用控制台输出
            print(f"文件数量更新 (控制台): {len(self.file_list)} 个文件")
        except Exception as e:
            print(f"更新文件数量失败: {e}")
    
    def selectOutputDir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_dir or "")
        if dir_path:
            self.output_dir = dir_path
            self.output_path_label.setText(self.output_dir)
    
    def startBatchProcessing(self):
        """开始批量处理"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先添加要处理的文件！")
            return
        
        if not self.output_dir:
            QMessageBox.warning(self, "警告", "请先选择输出目录！")
            return
        
        try:
            # 获取配置信息
            if self.individual_config_radio.isChecked():
                # 单独配置模式 - 检查是否所有文件都有配置
                missing_configs = []
                for file_path in self.file_list:
                    if file_path not in self.file_configs:
                        missing_configs.append(os.path.basename(file_path))
                
                if missing_configs:
                    missing_list = '\n'.join(missing_configs[:5])  # 只显示前5个
                    if len(missing_configs) > 5:
                        missing_list += f'\n... 还有 {len(missing_configs) - 5} 个文件'
                    
                    QMessageBox.warning(
                        self, "配置不完整", 
                        f"以下文件尚未配置，请先配置后再开始处理：\n\n{missing_list}"
                    )
                    return
                
                file_configs = self.file_configs.copy()
                global_config = None
            else:
                # 统一配置模式
                conversion_type = self.conversion_combo.currentText()
                voice_type = self.voice_combo.currentText().split(' - ')[0]
                speed = self.speed_slider.value()
                volume = self.volume_slider.value()
                quality = self.quality_combo.currentText()
                
                voice_params = {
                    'voice_type': voice_type,
                    'speed': speed,
                    'volume': volume,
                    'quality': quality
                }
                
                global_config = {
                    'conversion_type': conversion_type,
                    **voice_params
                }
                
                file_configs = None
            
            # 重置进度
            self.overall_progress.setValue(0)
            self.current_file_progress.setValue(0)
            self.status_label.setText("状态: 正在准备...")
            self.current_file_label.setText("当前文件: 准备中...")
            
            # 禁用控件
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.add_files_btn.setEnabled(False)
            self.add_folder_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            
            # 清空日志
            self.log_text.clear()
            self.addLog("开始批量处理...")
            
            # 启动处理线程
            self.process_thread = BatchProcessThread(
                self.file_list, 
                self.output_dir, 
                file_configs,
                global_config
            )
            
            # 连接信号和槽
            self.process_thread.progress.connect(self.updateBatchProgress)
            self.process_thread.current_file.connect(self.updateCurrentFile)
            self.process_thread.file_completed.connect(self.onFileCompleted)
            self.process_thread.all_completed.connect(self.onAllCompleted)
            
            # 启动线程
            self.process_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动批量处理失败: {str(e)}")
            print(f"批量处理启动错误: {e}")
            import traceback
            traceback.print_exc()
            
            # 恢复控件状态
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.add_files_btn.setEnabled(True)
            self.add_folder_btn.setEnabled(True)
            self.remove_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
    
    def updateBatchProgress(self, progress):
        """更新总体进度"""
        try:
            if hasattr(self, 'overall_progress'):
                self.overall_progress.setValue(progress)
                self.overall_progress_label.setText(f"总体进度: {progress}%")
        except Exception as e:
            print(f"更新总体进度失败: {e}")
    
    def updateCurrentFile(self, file_name):
        """更新当前处理的文件"""
        try:
            if hasattr(self, 'current_file_label'):
                short_name = os.path.basename(file_name)
                self.current_file_label.setText(f"当前文件: {short_name}")
                self.status_label.setText(f"正在处理: {short_name}")
                # 重置当前文件进度
                if hasattr(self, 'current_file_progress'):
                    self.current_file_progress.setValue(0)
        except Exception as e:
            print(f"更新当前文件失败: {e}")

    def updateCurrentFileProgress(self, progress):
        """更新当前文件的处理进度"""
        try:
            if hasattr(self, 'current_file_progress'):
                self.current_file_progress.setValue(progress)
        except Exception as e:
            print(f"更新当前文件进度失败: {e}")
    
    def onFileCompleted(self, file_path, success, message):
        """文件处理完成"""
        try:
            short_name = os.path.basename(file_path)
            if success:
                self.addLog(f"✅ {short_name} 处理成功")
                self.current_file_progress.setValue(100)
            else:
                self.addLog(f"❌ {short_name} 处理失败: {message}")
                self.current_file_progress.setValue(0)
        except Exception as e:
            print(f"文件完成处理失败: {e}")
    
    def onAllCompleted(self):
        """所有文件处理完成"""
        try:
            self.status_label.setText("状态: 批量处理完成")
            self.current_file_label.setText("当前文件: 全部完成")
            self.overall_progress.setValue(100)
            self.current_file_progress.setValue(100)
            
            # 恢复控件状态
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.add_files_btn.setEnabled(True)
            self.add_folder_btn.setEnabled(True)
            self.remove_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
        
            # 显示完成对话框
            QMessageBox.information(
                self,
                "处理完成",
                f"批量处理已完成！\n处理了 {len(self.file_list)} 个文件。"
            )
        except Exception as e:
            print(f"完成处理失败: {e}")
    
    def stopBatchProcessing(self):
        """停止批量处理"""
        try:
            if self.process_thread and self.process_thread.isRunning():
                self.addLog("正在停止处理...")
                self.process_thread.is_running = False
                self.process_thread.quit()
                self.process_thread.wait(3000)  # 等待3秒
                
                if self.process_thread.isRunning():
                    self.process_thread.terminate()
                    self.process_thread.wait(2000)
                
                self.addLog("处理已停止")
                
            # 重置UI状态
            self.start_btn.setEnabled(True)
            self.start_btn.setText("开始批量处理")
            self.stop_btn.setEnabled(False)
            self.status_label.setText("状态: 处理已停止")
            
        except Exception as e:
            self.addLog(f"停止处理时出错: {e}")
            print(f"停止处理失败: {e}")
    
    def addLog(self, message):
        """添加日志信息 - 增强版本，防止Qt对象被删除的错误"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        try:
            # 尝试更新UI日志
            if hasattr(self, 'log_text') and self.log_text is not None:
                # 检查Qt对象是否有效
                try:
                    # 这是一个轻量级的检查，看对象是否还有效
                    self.log_text.objectName()
                    
                    # 如果对象有效，添加日志
                    self.log_text.append(formatted_message)
                    
                    # 滚动到底部
                    cursor = self.log_text.textCursor()
                    cursor.movePosition(cursor.End)
                    self.log_text.setTextCursor(cursor)
                    
                    # 强制刷新UI
                    QApplication.processEvents()
                    
                except RuntimeError:
                    # Qt对象已被删除，回退到控制台输出
                    print(f"日志 (控制台): {formatted_message}")
            else:
                # 如果日志组件不存在，使用控制台输出
                print(f"日志 (控制台): {formatted_message}")
                
        except Exception as e:
            # 任何其他错误，都回退到控制台输出
            print(f"日志 (控制台): {formatted_message}")
            print(f"日志系统错误: {e}")
        
        # 同时输出到控制台（作为备份）
        print(formatted_message)

    def onConfigModeChanged(self):
        """配置模式改变时的处理"""
        is_individual = self.individual_config_radio.isChecked()
        
        # 显示/隐藏相关控件
        self.file_selection_label.setVisible(is_individual and len(self.file_list) == 0)
        self.current_config_file_label.setVisible(is_individual)
        self.apply_to_all_btn.setVisible(is_individual)
        
        if is_individual:
            # 切换到单独配置模式
            self.updateConfigPanelForIndividual()
        else:
            # 切换到统一配置模式
            self.file_selection_label.setVisible(False)
            self.current_config_file_label.setVisible(False)
            self.loadDefaultConfig()

    def onConfigChanged(self):
        """配置改变时的处理"""
        if self.individual_config_radio.isChecked():
            # 在单独配置模式下，保存当前选中文件的配置
            selected_items = self.file_list_widget.selectedItems()
            if selected_items:
                file_path = selected_items[0].data(Qt.UserRole)
                if file_path:
                    self.saveCurrentConfig(file_path)

    def saveCurrentConfig(self, file_path):
        """保存当前配置到指定文件"""
        config = {
            'conversion_type': self.conversion_combo.currentText(),
            'voice_type': self.voice_combo.currentText().split(' - ')[0],
            'speed': self.speed_slider.value(),
            'volume': self.volume_slider.value(),
            'quality': self.quality_combo.currentText()
        }
        self.file_configs[file_path] = config
        print(f"已保存文件配置: {os.path.basename(file_path)} -> {config['conversion_type']}")

    def loadConfigForFile(self, file_path):
        """加载指定文件的配置"""
        if file_path in self.file_configs:
            config = self.file_configs[file_path]
        else:
            # 如果没有配置，使用默认配置
            config = self.getDefaultConfig()
            self.file_configs[file_path] = config
        
        # 更新UI控件
        self.conversion_combo.setCurrentText(config['conversion_type'])
        
        # 查找匹配的发音人
        voice_type = config['voice_type']
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemText(i).startswith(voice_type):
                self.voice_combo.setCurrentIndex(i)
                break
        
        self.speed_slider.setValue(config['speed'])
        self.volume_slider.setValue(config['volume'])
        self.quality_combo.setCurrentText(config['quality'])
        
        print(f"已加载文件配置: {os.path.basename(file_path)} -> {config['conversion_type']}")

    def getDefaultConfig(self):
        """获取默认配置"""
        return {
            'conversion_type': '智能转换',
            'voice_type': 'xiaoyan',
            'speed': 100,
            'volume': 80,
            'quality': '高质量'
        }

    def loadDefaultConfig(self):
        """加载默认配置到UI"""
        config = self.getDefaultConfig()
        self.conversion_combo.setCurrentText(config['conversion_type'])
        
        voice_type = config['voice_type']
        for i in range(self.voice_combo.count()):
            if self.voice_combo.itemText(i).startswith(voice_type):
                self.voice_combo.setCurrentIndex(i)
                break
        
        self.speed_slider.setValue(config['speed'])
        self.volume_slider.setValue(config['volume'])
        self.quality_combo.setCurrentText(config['quality'])

    def applyConfigToAll(self):
        """将当前配置应用到所有文件"""
        if not self.file_list:
            QMessageBox.information(self, "提示", "没有文件可以应用配置")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认操作", 
            f"确定要将当前配置应用到所有 {len(self.file_list)} 个文件吗？\n\n这将覆盖所有文件的现有配置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            current_config = {
                'conversion_type': self.conversion_combo.currentText(),
                'voice_type': self.voice_combo.currentText().split(' - ')[0],
                'speed': self.speed_slider.value(),
                'volume': self.volume_slider.value(),
                'quality': self.quality_combo.currentText()
            }
            
            # 应用配置到所有文件
            for file_path in self.file_list:
                self.file_configs[file_path] = current_config.copy()
            
            QMessageBox.information(self, "完成", f"已将配置应用到所有 {len(self.file_list)} 个文件")
            print(f"已将配置应用到所有文件: {current_config['conversion_type']}")

    def resetCurrentConfig(self):
        """重置当前配置为默认值"""
        if self.individual_config_radio.isChecked():
            selected_items = self.file_list_widget.selectedItems()
            if selected_items:
                file_path = selected_items[0].data(Qt.UserRole)
                if file_path:
                    # 重置选中文件的配置
                    default_config = self.getDefaultConfig()
                    self.file_configs[file_path] = default_config
                    self.loadConfigForFile(file_path)
                    QMessageBox.information(self, "完成", f"已重置 {os.path.basename(file_path)} 的配置")
                else:
                    QMessageBox.information(self, "提示", "请先选择一个文件")
            else:
                QMessageBox.information(self, "提示", "请先选择一个文件")
        else:
            # 统一配置模式下，重置全局配置
            self.loadDefaultConfig()
            QMessageBox.information(self, "完成", "已重置为默认配置")

    def updateConfigPanelForIndividual(self):
        """更新配置面板以支持单独配置模式"""
        if len(self.file_list) == 0:
            self.file_selection_label.setVisible(True)
            self.current_config_file_label.setVisible(False)
        else:
            self.file_selection_label.setVisible(False)
            selected_items = self.file_list_widget.selectedItems()
            if selected_items:
                file_path = selected_items[0].data(Qt.UserRole)
                if file_path:
                    self.current_config_file_label.setText(f"配置文件: {os.path.basename(file_path)}")
                    self.current_config_file_label.setVisible(True)
                    self.file_selection_label.setVisible(False)
                    # 加载该文件的配置
                    self.loadConfigForFile(file_path)
                else:
                    self.current_config_file_label.setVisible(False)
                    self.file_selection_label.setVisible(True)
            else:
                self.current_config_file_label.setText("请选择一个文件进行配置")
                self.current_config_file_label.setVisible(True)

    def onFileSelectionChanged(self):
        """文件选择改变时的处理"""
        if self.individual_config_radio.isChecked():
            selected_items = self.file_list_widget.selectedItems()
            if selected_items:
                file_path = selected_items[0].data(Qt.UserRole)
                if file_path:
                    self.current_config_file_label.setText(f"配置文件: {os.path.basename(file_path)}")
                    self.current_config_file_label.setVisible(True)
                    self.file_selection_label.setVisible(False)
                    # 加载该文件的配置
                    self.loadConfigForFile(file_path)
                else:
                    self.current_config_file_label.setVisible(False)
                    self.file_selection_label.setVisible(True)
            else:
                self.current_config_file_label.setText("请选择一个文件进行配置")
                self.current_config_file_label.setVisible(True)
                self.file_selection_label.setVisible(False)

    def viewAllConfigurations(self):
        """查看所有文件的配置 - 新增功能"""
        if not self.file_list:
            QMessageBox.information(self, "提示", "没有文件可以查看配置")
            return
        
        # 创建配置查看对话框
        config_dialog = QDialog(self)
        config_dialog.setWindowTitle("文件配置总览")
        config_dialog.setModal(True)
        config_dialog.resize(700, 500)
        
        layout = QVBoxLayout(config_dialog)
        
        # 标题
        title_label = QLabel(f"所有文件配置总览 (共 {len(self.file_list)} 个文件)")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078D7; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 配置统计
        stats_label = QLabel()
        layout.addWidget(stats_label)
        
        # 表格显示
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["文件名", "转换类型", "发音人", "语速", "音量", "质量"])
        
        # 设置列宽
        table.setColumnWidth(0, 200)  # 文件名
        table.setColumnWidth(1, 100)  # 转换类型
        table.setColumnWidth(2, 120)  # 发音人
        table.setColumnWidth(3, 60)   # 语速
        table.setColumnWidth(4, 60)   # 音量
        table.setColumnWidth(5, 80)   # 质量
        
        # 填充数据
        table.setRowCount(len(self.file_list))
        config_stats = {}
        
        for i, file_path in enumerate(self.file_list):
            file_name = os.path.basename(file_path)
            
            # 获取文件配置
            if file_path in self.file_configs:
                config = self.file_configs[file_path]
            else:
                config = self.getDefaultConfig()
            
            conv_type = config['conversion_type']
            voice_params = config['voice_params']
            
            # 统计配置类型
            if conv_type in config_stats:
                config_stats[conv_type] += 1
            else:
                config_stats[conv_type] = 1
            
            # 设置表格内容
            table.setItem(i, 0, QTableWidgetItem(file_name))
            table.setItem(i, 1, QTableWidgetItem(conv_type))
            table.setItem(i, 2, QTableWidgetItem(voice_params['voice_type']))
            table.setItem(i, 3, QTableWidgetItem(f"{voice_params['speed']}%"))
            table.setItem(i, 4, QTableWidgetItem(f"{voice_params['volume']}%"))
            table.setItem(i, 5, QTableWidgetItem(voice_params['quality']))
        
        # 更新统计信息
        stats_text = "配置统计: "
        for conv_type, count in config_stats.items():
            stats_text += f"{conv_type}({count}个) "
        stats_label.setText(stats_text)
        stats_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        
        layout.addWidget(table)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        export_btn = QPushButton("导出配置")
        export_btn.clicked.connect(lambda: self.exportAllConfigurations())
        
        import_btn = QPushButton("导入配置")
        import_btn.clicked.connect(lambda: self.importAllConfigurations())
        
        reset_all_btn = QPushButton("重置所有")
        reset_all_btn.clicked.connect(lambda: self.resetAllConfigurations())
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(config_dialog.accept)
        
        button_layout.addWidget(export_btn)
        button_layout.addWidget(import_btn)
        button_layout.addWidget(reset_all_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        config_dialog.exec_()

    def exportAllConfigurations(self):
        """导出所有文件的配置"""
        if not self.file_configs:
            QMessageBox.information(self, "提示", "没有配置可以导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出批量配置", "batch_config.json", "JSON 文件 (*.json)"
        )
        
        if file_path:
            try:
                export_data = {
                    'file_list': self.file_list,
                    'file_configs': self.file_configs,
                    'export_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_files': len(self.file_list)
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "成功", f"配置已导出到: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出配置失败: {str(e)}")

    def importAllConfigurations(self):
        """导入所有文件的配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入批量配置", "", "JSON 文件 (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                if 'file_configs' not in import_data:
                    QMessageBox.warning(self, "错误", "无效的配置文件格式")
                    return
                
                imported_configs = import_data['file_configs']
                total_imported = 0
                
                # 只导入当前文件列表中存在的文件配置
                for file_path, config in imported_configs.items():
                    if file_path in self.file_list:
                        self.file_configs[file_path] = config
                        total_imported += 1
                
                QMessageBox.information(
                    self, "成功", 
                    f"已导入 {total_imported} 个文件的配置\n总配置数: {len(imported_configs)}"
                )
                
                # 刷新当前显示
                if self.individual_config_radio.isChecked():
                    self.updateConfigPanelForIndividual()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入配置失败: {str(e)}")

    def resetAllConfigurations(self):
        """重置所有文件的配置"""
        if not self.file_list:
            QMessageBox.information(self, "提示", "没有文件可以重置")
            return
        
        reply = QMessageBox.question(
            self, "确认重置", 
            f"确定要重置所有 {len(self.file_list)} 个文件的配置为默认设置吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            default_config = self.getDefaultConfig()
            reset_count = 0
            
            for file_path in self.file_list:
                self.file_configs[file_path] = default_config.copy()
                reset_count += 1
            
            QMessageBox.information(self, "完成", f"已重置 {reset_count} 个文件的配置")
            
            # 刷新当前显示
            if self.individual_config_radio.isChecked():
                self.updateConfigPanelForIndividual()

    def onSubtitleFileChanged(self, file_name):
        """字幕文件选择改变时的处理"""
        if file_name == "请先添加文件..." or not file_name:
            self.original_subtitle_text.clear()
            self.converted_subtitle_text.clear()
            self.export_subtitle_btn.setEnabled(False)
            return
        
        # 查找对应的文件路径
        file_path = None
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            if os.path.basename(item.data(Qt.UserRole)) == file_name:
                file_path = item.data(Qt.UserRole)
                break
        
        if file_path and file_path in self.subtitle_data:
            # 显示该文件的字幕数据
            subtitle_info = self.subtitle_data[file_path]
            self.original_subtitle_text.setPlainText(subtitle_info.get('original', ''))
            self.converted_subtitle_text.setPlainText(subtitle_info.get('converted', ''))
            
            # 如果有字幕内容，启用导出按钮
            if subtitle_info.get('original') or subtitle_info.get('converted'):
                self.export_subtitle_btn.setEnabled(True)
            else:
                self.export_subtitle_btn.setEnabled(False)
        else:
            # 清空显示
            self.original_subtitle_text.clear()
            self.converted_subtitle_text.clear()
            self.export_subtitle_btn.setEnabled(False)
    
    def clearSubtitles(self):
        """清空当前选择文件的字幕"""
        current_file = self.subtitle_file_combo.currentText()
        if current_file == "请先添加文件..." or not current_file:
            return
        
        # 查找对应的文件路径
        file_path = None
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            if os.path.basename(item.data(Qt.UserRole)) == current_file:
                file_path = item.data(Qt.UserRole)
                break
        
        if file_path and file_path in self.subtitle_data:
            # 清空字幕数据
            self.subtitle_data[file_path] = {'original': '', 'converted': ''}
            # 清空显示
            self.original_subtitle_text.clear()
            self.converted_subtitle_text.clear()
            self.export_subtitle_btn.setEnabled(False)
            
            self.addLog(f"已清空文件 {current_file} 的字幕数据")
    
    def exportCurrentSubtitle(self):
        """导出当前选择文件的字幕"""
        current_file = self.subtitle_file_combo.currentText()
        if current_file == "请先添加文件..." or not current_file:
            QMessageBox.warning(self, "警告", "请先选择要导出字幕的文件")
            return
        
        # 查找对应的文件路径
        file_path = None
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            if os.path.basename(item.data(Qt.UserRole)) == current_file:
                file_path = item.data(Qt.UserRole)
                break
        
        if not file_path or file_path not in self.subtitle_data:
            QMessageBox.warning(self, "警告", "找不到该文件的字幕数据")
            return
        
        subtitle_info = self.subtitle_data[file_path]
        
        # 确定要导出的字幕内容
        current_tab = self.subtitle_tabs.currentIndex()
        if current_tab == 0:  # 原始字幕
            content = subtitle_info.get('original', '')
            subtitle_type = "原始字幕"
        else:  # 转换后字幕
            content = subtitle_info.get('converted', '')
            subtitle_type = "转换后字幕"
        
        if not content.strip():
            QMessageBox.warning(self, "警告", f"该文件的{subtitle_type}为空，无法导出")
            return
        
        # 选择保存位置
        file_name = os.path.splitext(current_file)[0]
        default_name = f"{file_name}_{subtitle_type}.srt"
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, "导出字幕文件", default_name, 
            "SRT字幕文件 (*.srt);;所有文件 (*)"
        )
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                QMessageBox.information(self, "导出成功", f"字幕文件已保存到：\n{save_path}")
                self.addLog(f"已导出 {current_file} 的{subtitle_type}到：{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"保存字幕文件失败：\n{str(e)}")
    
    def updateSubtitleData(self, file_path, subtitle_type, content):
        """更新字幕数据"""
        if file_path not in self.subtitle_data:
            self.subtitle_data[file_path] = {'original': '', 'converted': ''}
        
        self.subtitle_data[file_path][subtitle_type] = content
        
        # 如果当前选择的文件是这个文件，则更新显示
        current_file = self.subtitle_file_combo.currentText()
        if current_file and current_file != "请先添加文件...":
            # 查找对应的文件路径
            selected_file_path = None
            for i in range(self.file_list_widget.count()):
                item = self.file_list_widget.item(i)
                if os.path.basename(item.data(Qt.UserRole)) == current_file:
                    selected_file_path = item.data(Qt.UserRole)
                    break
            
            if selected_file_path == file_path:
                # 更新显示
                if subtitle_type == 'original':
                    self.original_subtitle_text.setPlainText(content)
                elif subtitle_type == 'converted':
                    self.converted_subtitle_text.setPlainText(content)
                
                # 如果有字幕内容，启用导出按钮
                subtitle_info = self.subtitle_data[file_path]
                if subtitle_info.get('original') or subtitle_info.get('converted'):
                    self.export_subtitle_btn.setEnabled(True)
    
    def updateSubtitleFileList(self):
        """更新字幕文件选择列表"""
        current_selection = self.subtitle_file_combo.currentText()
        self.subtitle_file_combo.clear()
        
        if self.file_list_widget.count() == 0:
            self.subtitle_file_combo.addItem("请先添加文件...")
        else:
            # 添加所有文件到下拉列表
            for i in range(self.file_list_widget.count()):
                item = self.file_list_widget.item(i)
                file_name = os.path.basename(item.data(Qt.UserRole))
                self.subtitle_file_combo.addItem(file_name)
            
            # 尝试恢复之前的选择
            if current_selection and current_selection != "请先添加文件...":
                index = self.subtitle_file_combo.findText(current_selection)
                if index >= 0:
                    self.subtitle_file_combo.setCurrentIndex(index)

def show_batch_dialog(parent=None):
    """显示批量处理对话框"""
    dialog = BatchProcessDialog(parent)
    dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = BatchProcessDialog()
    dialog.show()
    sys.exit(app.exec_())