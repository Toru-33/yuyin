# -*- coding: utf-8 -*-
"""
本地化UI适配器
将本地化语音处理系统集成到现有的enhanced_UI和batch_processor中
"""

import os
import sys
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QCheckBox

# 导入本地化处理器
try:
    from local_speech_processor import LocalSpeechProcessor
    LOCAL_PROCESSOR_AVAILABLE = True
except ImportError:
    LOCAL_PROCESSOR_AVAILABLE = False
    print("⚠️ 本地化处理器不可用，请先安装依赖")

class LocalProcessingThread(QThread):
    """本地化处理线程，替代原有的ProcessThread"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    subtitle_ready = pyqtSignal(str, str)
    paused = pyqtSignal()
    resumed = pyqtSignal()
    
    def __init__(self, video_path, save_path, conversion_type, voice_params=None):
        super().__init__()
        self.video_path = video_path
        self.save_path = save_path
        self.conversion_type = conversion_type
        self.voice_params = voice_params or {}
        self.is_paused = False
        self.is_stopped = False
        
        # 初始化本地处理器
        if LOCAL_PROCESSOR_AVAILABLE:
            self.processor = LocalSpeechProcessor()
        else:
            self.processor = None
    
    def run(self):
        """运行本地化处理"""
        try:
            if not self.processor:
                self.finished.emit(False, "本地化处理器不可用，请安装依赖")
                return
            
            self.progress.emit(1, "开始本地化处理...")
            
            # 检查输入文件
            if not os.path.exists(self.video_path):
                self.finished.emit(False, f"视频文件不存在: {self.video_path}")
                return
            
            # 1. 从视频提取音频进行语音识别
            self.progress.emit(10, "从视频提取音频...")
            audio_file = self._extract_audio_from_video()
            
            if self.is_stopped:
                return
            
            # 2. 语音识别生成字幕
            self.progress.emit(20, "正在进行语音识别...")
            subtitle_content = self._transcribe_audio(audio_file)
            
            if self.is_stopped:
                return
            
            # 3. 创建临时字幕文件
            temp_subtitle_file = self._create_temp_subtitle_file(subtitle_content)
            
            # 4. 发送字幕准备信号
            self.subtitle_ready.emit(subtitle_content, "original")
            
            if self.is_stopped:
                return
            
            # 5. 根据转换类型处理视频
            self.progress.emit(40, "开始语音合成和视频处理...")
            
            success = self.processor.process_video_with_subtitles(
                self.video_path,
                temp_subtitle_file,
                self.save_path,
                self.conversion_type,
                self.voice_params,
                self._progress_callback
            )
            
            if success:
                self.finished.emit(True, "本地化处理完成")
            else:
                self.finished.emit(False, "本地化处理失败")
                
        except Exception as e:
            error_msg = f"本地化处理异常: {str(e)}"
            print(f"❌ {error_msg}")
            self.finished.emit(False, error_msg)
    
    def _extract_audio_from_video(self):
        """从视频提取音频"""
        try:
            from moviepy.editor import VideoFileClip
            
            video_path = Path(self.video_path)
            audio_file = video_path.parent / f"{video_path.stem}_extracted.wav"
            
            with VideoFileClip(str(video_path)) as video:
                if video.audio:
                    video.audio.write_audiofile(str(audio_file), verbose=False, logger=None)
                else:
                    raise Exception("视频文件没有音频轨道")
            
            return str(audio_file)
            
        except Exception as e:
            raise Exception(f"音频提取失败: {str(e)}")
    
    def _transcribe_audio(self, audio_file):
        """语音识别"""
        try:
            # 根据转换类型确定识别语言
            if "英文" in self.conversion_type:
                language = "en"
            elif "中文" in self.conversion_type:
                language = "zh"
            else:
                language = "auto"
            
            result = self.processor.transcribe_audio(
                audio_file, 
                language=language,
                progress_callback=self._transcribe_progress_callback
            )
            
            return self._format_subtitle_content(result)
            
        except Exception as e:
            raise Exception(f"语音识别失败: {str(e)}")
    
    def _format_subtitle_content(self, transcribe_result):
        """格式化字幕内容为SRT格式"""
        subtitle_lines = []
        
        if 'segments' in transcribe_result and transcribe_result['segments']:
            # 使用分段信息
            for i, segment in enumerate(transcribe_result['segments']):
                subtitle_lines.append(str(i + 1))
                
                start_time = self._seconds_to_srt_time(segment.get('start', 0))
                end_time = self._seconds_to_srt_time(segment.get('end', segment.get('start', 0) + 3))
                subtitle_lines.append(f"{start_time} --> {end_time}")
                
                text = segment.get('text', '').strip()
                subtitle_lines.append(text)
                subtitle_lines.append("")  # 空行分隔
        else:
            # 如果没有分段，创建一个整体字幕
            subtitle_lines = [
                "1",
                "00:00:00,000 --> 00:00:10,000",
                transcribe_result.get('text', ''),
                ""
            ]
        
        return "\n".join(subtitle_lines)
    
    def _seconds_to_srt_time(self, seconds):
        """将秒数转换为SRT时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _create_temp_subtitle_file(self, content):
        """创建临时字幕文件"""
        temp_dir = Path(self.save_path).parent / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / "transcribed_subtitle.srt"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(temp_file)
    
    def _progress_callback(self, progress, message):
        """进度回调"""
        if not self.is_stopped:
            self.progress.emit(progress, message)
    
    def _transcribe_progress_callback(self, progress, message):
        """语音识别进度回调"""
        # 映射到总进度的20-40%
        mapped_progress = 20 + (progress * 0.2)
        self._progress_callback(int(mapped_progress), message)
    
    def pause(self):
        """暂停处理"""
        self.is_paused = True
        self.paused.emit()
    
    def resume(self):
        """恢复处理"""
        self.is_paused = False
        self.resumed.emit()
    
    def stop(self):
        """停止处理"""
        self.is_stopped = True


class LocalProcessingDialog(QDialog):
    """本地化处理设置对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("本地化处理设置")
        self.setModal(True)
        self.resize(400, 300)
        
        self.use_local_processing = False
        self.setupUI()
    
    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🎯 本地化语音处理")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # 说明
        description = QLabel(
            "本地化处理使用以下开源模型：\n"
            "• Whisper - 语音识别\n"
            "• pyttsx3 - 语音合成\n"
            "• Argos Translate - 文本翻译\n\n"
            "优势：\n"
            "✅ 完全离线运行\n"
            "✅ 无API调用限制\n"
            "✅ 更好的隐私保护\n"
            "✅ 长期使用成本更低"
        )
        description.setStyleSheet("margin: 10px; line-height: 1.5;")
        layout.addWidget(description)
        
        # 检查可用性
        if LOCAL_PROCESSOR_AVAILABLE:
            processor = LocalSpeechProcessor()
            model_info = processor.get_model_info()
            
            status_text = "📊 模型状态：\n"
            for model_type, info in model_info.items():
                status = "✅ 可用" if info['available'] else "❌ 不可用"
                status_text += f"• {model_type}: {status}\n"
            
            status_label = QLabel(status_text)
            layout.addWidget(status_label)
            
            # 启用选项
            self.enable_checkbox = QCheckBox("使用本地化处理")
            self.enable_checkbox.setChecked(True)
            layout.addWidget(self.enable_checkbox)
            
        else:
            error_label = QLabel(
                "❌ 本地化处理器不可用\n\n"
                "请运行以下命令安装依赖：\n"
                "python install_local_dependencies.py"
            )
            error_label.setStyleSheet("color: red; margin: 10px;")
            layout.addWidget(error_label)
            
            self.enable_checkbox = QCheckBox("使用本地化处理")
            self.enable_checkbox.setEnabled(False)
            layout.addWidget(self.enable_checkbox)
        
        # 按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)
        
        self.setLayout(layout)
    
    def accept(self):
        """确认"""
        if hasattr(self, 'enable_checkbox'):
            self.use_local_processing = self.enable_checkbox.isChecked()
        super().accept()


class LocalUIAdapter:
    """本地化UI适配器"""
    
    @staticmethod
    def patch_enhanced_ui(main_window):
        """为enhanced_UI添加本地化处理支持"""
        
        # 保存原始的startProcessing方法
        original_start_processing = main_window.startProcessing
        
        def enhanced_start_processing():
            """增强的开始处理方法"""
            # 显示本地化处理选择对话框
            dialog = LocalProcessingDialog(main_window)
            if dialog.exec_() == QDialog.Accepted and dialog.use_local_processing:
                # 使用本地化处理
                main_window._start_local_processing()
            else:
                # 使用原始API处理
                original_start_processing()
        
        def _start_local_processing():
            """开始本地化处理"""
            try:
                # 获取处理参数
                video_path = main_window.file_input.path
                save_path = main_window.output_path_input.text()
                conversion_type = main_window.conversion_combo.currentText()
                
                # 语音参数
                voice_params = {
                    'speed': main_window.speed_slider.value() if hasattr(main_window, 'speed_slider') else 150,
                    'volume': main_window.volume_slider.value() / 100.0 if hasattr(main_window, 'volume_slider') else 0.8
                }
                
                # 创建本地化处理线程
                main_window.process_thread = LocalProcessingThread(
                    video_path, save_path, conversion_type, voice_params
                )
                
                # 连接信号
                main_window.process_thread.progress.connect(main_window.update_progress)
                main_window.process_thread.finished.connect(main_window.on_process_finished)
                main_window.process_thread.subtitle_ready.connect(main_window.on_subtitle_ready)
                
                # 开始处理
                main_window.process_thread.start()
                main_window.set_controls_enabled(False)
                
                print("🚀 开始本地化处理...")
                
            except Exception as e:
                QMessageBox.critical(main_window, "错误", f"本地化处理启动失败: {str(e)}")
        
        # 替换方法
        main_window.startProcessing = enhanced_start_processing
        main_window._start_local_processing = _start_local_processing
        
        # 添加菜单项
        if hasattr(main_window, 'menubar'):
            local_menu = main_window.menubar.addMenu("本地化处理")
            
            install_action = local_menu.addAction("安装依赖")
            install_action.triggered.connect(lambda: main_window._show_install_guide())
            
            test_action = local_menu.addAction("测试模型")
            test_action.triggered.connect(lambda: main_window._test_local_models())
        
        def _show_install_guide():
            """显示安装指南"""
            QMessageBox.information(
                main_window,
                "安装本地化依赖",
                "请在命令行中运行：\n\n"
                "python install_local_dependencies.py\n\n"
                "这将自动安装所有必需的本地化模型。"
            )
        
        def _test_local_models():
            """测试本地模型"""
            if LOCAL_PROCESSOR_AVAILABLE:
                processor = LocalSpeechProcessor()
                info = processor.get_model_info()
                
                status_text = "本地模型状态：\n\n"
                for model_type, model_info in info.items():
                    status = "✅ 可用" if model_info['available'] else "❌ 不可用"
                    status_text += f"{model_type}: {status}\n"
                
                QMessageBox.information(main_window, "模型状态", status_text)
            else:
                QMessageBox.warning(
                    main_window,
                    "模型不可用",
                    "本地化处理器不可用，请先安装依赖。"
                )
        
        main_window._show_install_guide = _show_install_guide
        main_window._test_local_models = _test_local_models
        
        print("✅ enhanced_UI 本地化适配完成")


# 使用示例
def apply_local_patches(main_window):
    """应用本地化补丁"""
    print("🔧 正在应用本地化UI补丁...")
    
    # 适配主窗口
    LocalUIAdapter.patch_enhanced_ui(main_window)
    
    print("✅ 本地化UI补丁应用完成")


if __name__ == "__main__":
    print("🔧 本地化UI适配器")
    print("请在主程序中导入并使用 apply_local_patches 函数") 