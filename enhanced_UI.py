# -*- coding: utf-8 -*-
"""
增强版语音替换工具UI
包含现代化界面设计、进度提示、设置管理、预览功能等
"""

import sys
import os
import json
import threading
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtCore, QtGui, QtWidgets

# 导入原有功能模块
import addNewSound
import addSrt
import video_to_txt
import voice_get_text
import syntheticSpeech
import syntheticSpeechCn
import syntheticSpeechTranslateToEn
import syntheticSpeechTranslateToCn
import generateWav
import batch_processor

class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi()
        self.loadSettings()
    
    def setupUi(self):
        self.setWindowTitle("设置")
        self.setFixedSize(500, 400)
        layout = QVBoxLayout()
        
        # API设置组
        api_group = QGroupBox("API 配置")
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
        api_layout.addRow("百度翻译 APPID:", self.baidu_appid)
        api_layout.addRow("百度翻译 AppKey:", self.baidu_appkey)
        
        api_group.setLayout(api_layout)
        
        # 语音设置组
        voice_group = QGroupBox("语音参数")
        voice_layout = QFormLayout()
        
        self.voice_speed = QSlider(Qt.Horizontal)
        self.voice_speed.setRange(50, 200)
        self.voice_speed.setValue(100)
        self.speed_label = QLabel("100%")
        
        self.voice_volume = QSlider(Qt.Horizontal)
        self.voice_volume.setRange(0, 100)
        self.voice_volume.setValue(80)
        self.volume_label = QLabel("80%")
        
        self.voice_speed.valueChanged.connect(lambda v: self.speed_label.setText(f"{v}%"))
        self.voice_volume.valueChanged.connect(lambda v: self.volume_label.setText(f"{v}%"))
        
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.voice_speed)
        speed_layout.addWidget(self.speed_label)
        
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.voice_volume)
        volume_layout.addWidget(self.volume_label)
        
        voice_layout.addRow("语音速度:", speed_layout)
        voice_layout.addRow("语音音量:", volume_layout)
        
        voice_group.setLayout(voice_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(self.saveSettings)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addWidget(api_group)
        layout.addWidget(voice_group)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def loadSettings(self):
        """加载设置"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.xunfei_appid.setText(settings.get('xunfei_appid', ''))
                self.xunfei_apikey.setText(settings.get('xunfei_apikey', ''))
                self.xunfei_apisecret.setText(settings.get('xunfei_apisecret', ''))
                self.baidu_appid.setText(settings.get('baidu_appid', ''))
                self.baidu_appkey.setText(settings.get('baidu_appkey', ''))
                self.voice_speed.setValue(settings.get('voice_speed', 100))
                self.voice_volume.setValue(settings.get('voice_volume', 80))
        except:
            pass
    
    def saveSettings(self):
        """保存设置"""
        settings = {
            'xunfei_appid': self.xunfei_appid.text(),
            'xunfei_apikey': self.xunfei_apikey.text(),
            'xunfei_apisecret': self.xunfei_apisecret.text(),
            'baidu_appid': self.baidu_appid.text(),
            'baidu_appkey': self.baidu_appkey.text(),
            'voice_speed': self.voice_speed.value(),
            'voice_volume': self.voice_volume.value()
        }
        
        with open('settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        
        QMessageBox.information(self, "提示", "设置保存成功！")
        self.accept()

class ProcessThread(QThread):
    """处理线程"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, video_path, save_path, conversion_type):
        super().__init__()
        self.video_path = video_path
        self.save_path = save_path
        self.conversion_type = conversion_type
    
    def run(self):
        try:
            self.status.emit("正在提取音频...")
            self.progress.emit(10)
            
            # 提取音频
            wav_path = generateWav.run(self.video_path, self.save_path)
            
            self.status.emit("正在生成无声视频...")
            self.progress.emit(25)
            
            # 生成无声视频
            video_without_sound = addNewSound.del_audio(self.video_path, self.save_path)
            
            self.status.emit("正在识别语音...")
            self.progress.emit(40)
            
            # 生成字幕文件
            video_to_txt.run(wav_path, self.save_path)
            
            self.status.emit("正在合成新语音...")
            self.progress.emit(60)
            
            # 根据转换类型处理
            filename = 'subtitle.srt'
            subtitle_file = os.path.join(self.save_path, filename)
            
            if self.conversion_type == "中文转英文":
                syntheticSpeechTranslateToEn.run(video_without_sound, subtitle_file)
            elif self.conversion_type == "中文转中文":
                syntheticSpeechCn.run(video_without_sound, subtitle_file)
            elif self.conversion_type == "英文转中文":
                syntheticSpeechTranslateToCn.run(video_without_sound, subtitle_file)
            elif self.conversion_type == "英文转英文":
                syntheticSpeech.run(video_without_sound, subtitle_file)
            
            self.status.emit("处理完成！")
            self.progress.emit(100)
            self.finished.emit(True, "视频处理成功完成！")
            
        except Exception as e:
            self.finished.emit(False, f"处理失败：{str(e)}")

class EnhancedMainWindow(QMainWindow):
    """增强版主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setupUi()
        self.setStyleSheet(self.getStyleSheet())
        
    def setupUi(self):
        self.setWindowTitle("智能多语言视频语音转换系统 v2.0")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        
        # 设置窗口图标
        self.setWindowIcon(QIcon("icon.png"))
        
        # 中央组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # 标题区域
        title_layout = self.createTitleSection()
        main_layout.addLayout(title_layout)
        
        # 文件选择区域
        file_section = self.createFileSection()
        main_layout.addWidget(file_section)
        
        # 转换设置区域
        conversion_section = self.createConversionSection()
        main_layout.addWidget(conversion_section)
        
        # 进度区域
        progress_section = self.createProgressSection()
        main_layout.addWidget(progress_section)
        
        # 操作按钮区域
        button_section = self.createButtonSection()
        main_layout.addWidget(button_section)
        
        # 状态栏
        self.createStatusBar()
        
        # 菜单栏
        self.createMenuBar()
        
    def createTitleSection(self):
        """创建标题区域"""
        layout = QVBoxLayout()
        
        title_label = QLabel("智能多语言视频语音转换系统")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        
        subtitle_label = QLabel("支持中英文互转，让您的视频内容触达更多用户")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        
        return layout
    
    def createFileSection(self):
        """创建文件选择区域"""
        group = QGroupBox("文件选择")
        group.setObjectName("fileGroup")
        layout = QVBoxLayout(group)
        
        # 输入文件
        input_layout = QHBoxLayout()
        input_label = QLabel("视频文件:")
        input_label.setMinimumWidth(80)
        
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("请选择要处理的视频文件...")
        self.input_path.setAcceptDrops(True)
        
        input_btn = QPushButton("浏览...")
        input_btn.setMaximumWidth(80)
        input_btn.clicked.connect(self.selectInputFile)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(input_btn)
        
        # 输出目录
        output_layout = QHBoxLayout()
        output_label = QLabel("输出目录:")
        output_label.setMinimumWidth(80)
        
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("请选择输出目录...")
        
        output_btn = QPushButton("浏览...")
        output_btn.setMaximumWidth(80)
        output_btn.clicked.connect(self.selectOutputDir)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_btn)
        
        layout.addLayout(input_layout)
        layout.addLayout(output_layout)
        
        return group
    
    def createConversionSection(self):
        """创建转换设置区域"""
        group = QGroupBox("转换设置")
        layout = QHBoxLayout(group)
        
        # 转换类型
        type_layout = QVBoxLayout()
        type_label = QLabel("转换类型:")
        self.conversion_combo = QComboBox()
        self.conversion_combo.addItems([
            "中文转英文", "中文转中文", "英文转中文", "英文转英文"
        ])
        self.conversion_combo.setMinimumHeight(40)
        
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.conversion_combo)
        
        # 语音选择
        voice_layout = QVBoxLayout()
        voice_label = QLabel("语音选择:")
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "标准女声", "标准男声", "甜美女声", "磁性男声"
        ])
        self.voice_combo.setMinimumHeight(40)
        
        voice_layout.addWidget(voice_label)
        voice_layout.addWidget(self.voice_combo)
        
        # 质量设置
        quality_layout = QVBoxLayout()
        quality_label = QLabel("输出质量:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "标准质量", "高质量", "超清质量"
        ])
        self.quality_combo.setMinimumHeight(40)
        
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_combo)
        
        layout.addLayout(type_layout)
        layout.addLayout(voice_layout)
        layout.addLayout(quality_layout)
        
        return group
    
    def createProgressSection(self):
        """创建进度区域"""
        group = QGroupBox("处理进度")
        layout = QVBoxLayout(group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setTextVisible(True)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        
        return group
    
    def createButtonSection(self):
        """创建按钮区域"""
        group = QGroupBox("操作")
        layout = QHBoxLayout(group)
        layout.setSpacing(15)
        
        # 预览按钮
        self.preview_btn = QPushButton("预览效果")
        self.preview_btn.setMinimumHeight(45)
        self.preview_btn.setObjectName("previewButton")
        self.preview_btn.clicked.connect(self.previewResult)
        
        # 开始处理按钮
        self.process_btn = QPushButton("开始转换")
        self.process_btn.setMinimumHeight(45)
        self.process_btn.setObjectName("processButton")
        self.process_btn.clicked.connect(self.startProcessing)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止处理")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stopProcessing)
        
        # 播放结果按钮
        self.play_btn = QPushButton("播放结果")
        self.play_btn.setMinimumHeight(45)
        self.play_btn.setObjectName("playButton")
        self.play_btn.clicked.connect(self.playResult)
        
        layout.addWidget(self.preview_btn)
        layout.addWidget(self.process_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.play_btn)
        
        return group
    
    def createMenuBar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        new_action = QAction('新建项目', self)
        new_action.setShortcut('Ctrl+N')
        file_menu.addAction(new_action)
        
        open_action = QAction('打开项目', self)
        open_action.setShortcut('Ctrl+O')
        file_menu.addAction(open_action)
        
        save_action = QAction('保存项目', self)
        save_action.setShortcut('Ctrl+S')
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.openSettings)
        tools_menu.addAction(settings_action)
        
        batch_action = QAction('批量处理', self)
        batch_action.triggered.connect(self.openBatchProcessor)
        tools_menu.addAction(batch_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)
    
    def createStatusBar(self):
        """创建状态栏"""
        self.statusBar().showMessage("就绪")
    
    def selectInputFile(self):
        """选择输入文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", 
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv);;所有文件 (*)"
        )
        if file_path:
            self.input_path.setText(file_path)
    
    def selectOutputDir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", ""
        )
        if dir_path:
            self.output_path.setText(dir_path)
    
    def openSettings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec_()
    
    def openBatchProcessor(self):
        """打开批量处理对话框"""
        batch_processor.show_batch_dialog(self)
    
    def previewResult(self):
        """预览效果"""
        QMessageBox.information(self, "预览", "预览功能正在开发中...")
    
    def startProcessing(self):
        """开始处理"""
        video_path = self.input_path.text().strip()
        save_path = self.output_path.text().strip()
        
        if not video_path or not save_path:
            QMessageBox.warning(self, "警告", "请选择视频文件和输出目录！")
            return
        
        if not os.path.exists(video_path):
            QMessageBox.warning(self, "警告", "视频文件不存在！")
            return
        
        # 禁用按钮
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 重置进度
        self.progress_bar.setValue(0)
        
        # 启动处理线程
        conversion_type = self.conversion_combo.currentText()
        self.process_thread = ProcessThread(video_path, save_path, conversion_type)
        self.process_thread.progress.connect(self.progress_bar.setValue)
        self.process_thread.status.connect(self.status_label.setText)
        self.process_thread.finished.connect(self.onProcessFinished)
        self.process_thread.start()
    
    def stopProcessing(self):
        """停止处理"""
        if hasattr(self, 'process_thread') and self.process_thread.isRunning():
            self.process_thread.terminate()
            self.process_thread.wait()
        
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("已停止")
    
    def onProcessFinished(self, success, message):
        """处理完成回调"""
        self.process_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.status_label.setText("处理完成")
        else:
            QMessageBox.critical(self, "错误", message)
            self.status_label.setText("处理失败")
    
    def playResult(self):
        """播放结果"""
        save_path = self.output_path.text().strip()
        if save_path:
            result_path = os.path.join(save_path, "NewVideo.mp4")
            if os.path.exists(result_path):
                os.system(f'start "" "{result_path}"')
            else:
                QMessageBox.warning(self, "警告", "结果文件不存在！")
        else:
            QMessageBox.warning(self, "警告", "请先选择输出目录！")
    
    def showAbout(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
            "智能多语言视频语音转换系统 v2.0\n\n"
            "一个基于AI技术的视频语音转换工具\n"
            "支持中英文互转，适用于教育、培训等场景\n\n"
            "技术支持：科大讯飞、百度翻译")
    
    def getStyleSheet(self):
        """获取样式表"""
        return """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        #titleLabel {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
            margin: 20px 0 10px 0;
        }
        
        #subtitleLabel {
            font-size: 14px;
            color: #7f8c8d;
            margin-bottom: 20px;
        }
        
        QGroupBox {
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
            border: 2px solid #bdc3c7;
            border-radius: 8px;
            margin-top: 15px;
            padding-top: 10px;
            background-color: white;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            background-color: white;
        }
        
        QLineEdit {
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            background-color: white;
        }
        
        QLineEdit:focus {
            border-color: #3498db;
        }
        
        QComboBox {
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            background-color: white;
        }
        
        QComboBox:focus {
            border-color: #3498db;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 30px;
        }
        
        QComboBox::down-arrow {
            image: url(down_arrow.png);
            width: 12px;
            height: 12px;
        }
        
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 13px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #2980b9;
        }
        
        QPushButton:pressed {
            background-color: #21618c;
        }
        
        QPushButton:disabled {
            background-color: #bdc3c7;
            color: #7f8c8d;
        }
        
        #processButton {
            background-color: #27ae60;
        }
        
        #processButton:hover {
            background-color: #229954;
        }
        
        #stopButton {
            background-color: #e74c3c;
        }
        
        #stopButton:hover {
            background-color: #c0392b;
        }
        
        #previewButton {
            background-color: #f39c12;
        }
        
        #previewButton:hover {
            background-color: #e67e22;
        }
        
        #playButton {
            background-color: #9b59b6;
        }
        
        #playButton:hover {
            background-color: #8e44ad;
        }
        
        QProgressBar {
            border: 2px solid #bdc3c7;
            border-radius: 6px;
            text-align: center;
            font-weight: bold;
            background-color: white;
        }
        
        QProgressBar::chunk {
            background-color: #3498db;
            border-radius: 4px;
        }
        
        #statusLabel {
            font-size: 13px;
            color: #2c3e50;
            padding: 5px;
        }
        
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #bdc3c7;
        }
        
        QMenuBar::item {
            padding: 8px 15px;
            background-color: transparent;
        }
        
        QMenuBar::item:selected {
            background-color: #ecf0f1;
        }
        
        QStatusBar {
            background-color: white;
            border-top: 1px solid #bdc3c7;
        }
        """

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("智能多语言视频语音转换系统")
    app.setApplicationVersion("2.0")
    
    # 设置应用图标
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = EnhancedMainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 