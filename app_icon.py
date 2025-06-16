# -*- coding: utf-8 -*-
"""
应用程序图标管理模块
提供统一的图标管理和应用程序图标
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QColor
from PyQt5.QtSvg import QSvgRenderer

def create_app_icon():
    """创建应用程序主图标 - 一个简单的视频播放器样式图标"""
    # 创建一个64x64的pixmap
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 120, 215))  # 蓝色背景
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    # 绘制播放按钮三角形
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.setPen(QColor(255, 255, 255))
    
    # 三角形坐标 (播放按钮)
    triangle = [
        (20, 16),  # 左上
        (20, 48),  # 左下  
        (44, 32)   # 右中
    ]
    
    from PyQt5.QtCore import QPoint
    from PyQt5.QtGui import QPolygon
    
    points = [QPoint(x, y) for x, y in triangle]
    polygon = QPolygon(points)
    painter.drawPolygon(polygon)
    
    painter.end()
    
    return QIcon(pixmap)

def get_conversion_icon(conversion_type):
    """根据转换类型返回合适的图标名称"""
    icon_map = {
        "智能转换": "🧠",
        "中文转英文": "🔄",
        "中文转中文": "🔃",
        "英文转中文": "🔄",
        "英文转英文": "🔃"
    }
    return icon_map.get(conversion_type, "🔄")

def get_voice_icon(voice_name):
    """根据发音人性别返回合适的图标"""
    female_voices = ["xiaoyan", "xiaoxin", "aisxping", "Laura", "Emma"]
    male_voices = ["xiaoyu", "Alex"]
    
    if any(name in voice_name for name in female_voices):
        return "👩"
    elif any(name in voice_name for name in male_voices):
        return "👨"
    else:
        return "🎤"

def get_quality_icon(quality):
    """根据质量等级返回合适的图标"""
    quality_map = {
        "标准质量": "⭐",
        "高质量": "⭐⭐",
        "超清质量": "⭐⭐⭐"
    }
    return quality_map.get(quality, "⭐")

# 统一的图标主题
ICON_THEME = {
    "app": "🎬",
    "video": "🎥", 
    "audio": "🎵",
    "settings": "⚙️",
    "process": "▶️",
    "stop": "⏹️",
    "preview": "👁️",
    "batch": "📋",
    "folder": "📁",
    "file": "📄",
    "save": "💾",
    "export": "📤",
    "copy": "📋",
    "clear": "🗑️",
    "refresh": "🔄",
    "zoom_in": "🔍+",
    "zoom_out": "🔍-",
    "reset": "↺"
}

def get_themed_icon(icon_name):
    """获取主题图标"""
    return ICON_THEME.get(icon_name, "❓") 