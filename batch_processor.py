# -*- coding: utf-8 -*-
"""
批量处理模块
支持批量处理多个视频文件
"""

import os
import sys
import json
import threading
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

class BatchProcessThread(QThread):
    """批量处理线程"""
    progress = pyqtSignal(int)
    current_file = pyqtSignal(str)
    file_completed = pyqtSignal(str, bool, str)
    all_completed = pyqtSignal()
    
    def __init__(self, file_list, output_dir, conversion_type, settings):
        super().__init__()
        self.file_list = file_list
        self.output_dir = output_dir
        self.conversion_type = conversion_type
        self.settings = settings
        self.should_stop = False
        
    def run(self):
        total_files = len(self.file_list)
        
        for i, video_file in enumerate(self.file_list):
            if self.should_stop:
                break
                
            try:
                # 更新当前处理文件
                filename = os.path.basename(video_file)
                self.current_file.emit(f"正在处理: {filename}")
                
                # 为每个文件创建单独的输出目录
                file_output_dir = os.path.join(
                    self.output_dir, 
                    os.path.splitext(filename)[0]
                )
                os.makedirs(file_output_dir, exist_ok=True)
                
                # 处理单个文件
                self.process_single_file(video_file, file_output_dir)
                
                # 标记文件处理完成
                self.file_completed.emit(filename, True, "处理成功")
                
            except Exception as e:
                self.file_completed.emit(filename, False, str(e))
            
            # 更新总进度
            progress = int((i + 1) / total_files * 100)
            self.progress.emit(progress)
        
        self.all_completed.emit()
    
    def process_single_file(self, video_file, output_dir):
        """处理单个文件"""
        # 提取音频
        wav_path = generateWav.run(video_file, output_dir)
        
        # 生成无声视频
        video_without_sound = addNewSound.del_audio(video_file, output_dir)
        
        # 生成字幕文件
        video_to_txt.run(wav_path, output_dir)
        
        # 根据转换类型处理
        filename = 'subtitle.srt'
        subtitle_file = os.path.join(output_dir, filename)
        
        if self.conversion_type == "中文转英文":
            syntheticSpeechTranslateToEn.run(video_without_sound, subtitle_file)
        elif self.conversion_type == "中文转中文":
            syntheticSpeechCn.run(video_without_sound, subtitle_file)
        elif self.conversion_type == "英文转中文":
            syntheticSpeechTranslateToCn.run(video_without_sound, subtitle_file)
        elif self.conversion_type == "英文转英文":
            syntheticSpeech.run(video_without_sound, subtitle_file)
    
    def stop_processing(self):
        """停止处理"""
        self.should_stop = True

class BatchProcessDialog(QDialog):
    """批量处理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        self.file_list = []
        
    def setupUi(self):
        self.setWindowTitle("批量处理")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        # 文件列表区域
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout(file_group)
        
        # 文件操作按钮
        button_layout = QHBoxLayout()
        add_files_btn = QPushButton("添加文件")
        add_folder_btn = QPushButton("添加文件夹")
        remove_btn = QPushButton("移除选中")
        clear_btn = QPushButton("清空列表")
        
        add_files_btn.clicked.connect(self.addFiles)
        add_folder_btn.clicked.connect(self.addFolder)
        remove_btn.clicked.connect(self.removeSelected)
        clear_btn.clicked.connect(self.clearList)
        
        button_layout.addWidget(add_files_btn)
        button_layout.addWidget(add_folder_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        
        # 文件列表
        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        file_layout.addLayout(button_layout)
        file_layout.addWidget(self.file_list_widget)
        
        # 设置区域
        settings_group = QGroupBox("处理设置")
        settings_layout = QFormLayout(settings_group)
        
        # 输出目录
        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出目录...")
        output_btn = QPushButton("浏览...")
        output_btn.clicked.connect(self.selectOutputDir)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_btn)
        
        # 转换类型
        self.conversion_combo = QComboBox()
        self.conversion_combo.addItems([
            "中文转英文", "中文转中文", "英文转中文", "英文转英文"
        ])
        
        # 并发数量
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 4)
        self.concurrent_spin.setValue(1)
        
        settings_layout.addRow("输出目录:", output_layout)
        settings_layout.addRow("转换类型:", self.conversion_combo)
        settings_layout.addRow("并发数量:", self.concurrent_spin)
        
        # 进度区域
        progress_group = QGroupBox("处理进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.current_file_label = QLabel("等待开始...")
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        
        progress_layout.addWidget(QLabel("总进度:"))
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.current_file_label)
        progress_layout.addWidget(QLabel("处理日志:"))
        progress_layout.addWidget(self.log_text)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始处理")
        self.stop_btn = QPushButton("停止处理")
        self.close_btn = QPushButton("关闭")
        
        self.start_btn.clicked.connect(self.startProcessing)
        self.stop_btn.clicked.connect(self.stopProcessing)
        self.close_btn.clicked.connect(self.close)
        
        self.stop_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.close_btn)
        
        # 添加所有组件到主布局
        layout.addWidget(file_group)
        layout.addWidget(settings_group)
        layout.addWidget(progress_group)
        layout.addLayout(control_layout)
    
    def addFiles(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*)"
        )
        
        for file_path in files:
            if file_path not in self.file_list:
                self.file_list.append(file_path)
                self.file_list_widget.addItem(os.path.basename(file_path))
    
    def addFolder(self):
        """添加文件夹中的所有视频"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "选择包含视频文件的文件夹"
        )
        
        if folder_path:
            video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv']
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_list:
                            self.file_list.append(file_path)
                            self.file_list_widget.addItem(file)
    
    def removeSelected(self):
        """移除选中的文件"""
        selected_items = self.file_list_widget.selectedItems()
        for item in selected_items:
            row = self.file_list_widget.row(item)
            self.file_list_widget.takeItem(row)
            if row < len(self.file_list):
                self.file_list.pop(row)
    
    def clearList(self):
        """清空文件列表"""
        self.file_list_widget.clear()
        self.file_list.clear()
    
    def selectOutputDir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录"
        )
        if dir_path:
            self.output_path.setText(dir_path)
    
    def startProcessing(self):
        """开始批量处理"""
        if not self.file_list:
            QMessageBox.warning(self, "警告", "请先添加要处理的文件！")
            return
        
        output_dir = self.output_path.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 重置进度
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        # 启动处理线程
        conversion_type = self.conversion_combo.currentText()
        settings = {}  # 可以从设置文件加载
        
        self.process_thread = BatchProcessThread(
            self.file_list, output_dir, conversion_type, settings
        )
        
        self.process_thread.progress.connect(self.progress_bar.setValue)
        self.process_thread.current_file.connect(self.current_file_label.setText)
        self.process_thread.file_completed.connect(self.onFileCompleted)
        self.process_thread.all_completed.connect(self.onAllCompleted)
        
        self.process_thread.start()
        
        self.addLog("开始批量处理...")
    
    def stopProcessing(self):
        """停止处理"""
        if hasattr(self, 'process_thread') and self.process_thread.isRunning():
            self.process_thread.stop_processing()
            self.process_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.current_file_label.setText("已停止")
        self.addLog("处理已停止")
    
    def onFileCompleted(self, filename, success, message):
        """单个文件处理完成"""
        status = "成功" if success else "失败"
        log_message = f"{filename} - {status}: {message}"
        self.addLog(log_message)
    
    def onAllCompleted(self):
        """所有文件处理完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.current_file_label.setText("全部完成")
        self.addLog("批量处理完成！")
        
        QMessageBox.information(self, "完成", "所有文件处理完成！")
    
    def addLog(self, message):
        """添加日志信息"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.End)
        self.log_text.setTextCursor(cursor)

def show_batch_dialog(parent=None):
    """显示批量处理对话框"""
    dialog = BatchProcessDialog(parent)
    dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = BatchProcessDialog()
    dialog.show()
    sys.exit(app.exec_()) 