# -*- coding: utf-8 -*-
"""
路径配置管理模块
统一管理整个项目中的文件路径和命名规则
"""

import os

class PathConfig:
    """路径配置类 - 定义所有文件的标准命名和路径规则"""
    
    # 标准文件名定义
    EXTRACTED_AUDIO = "extractedAudio.wav"
    VIDEO_WITHOUT_AUDIO = "videoWithoutAudio.mp4"
    ORIGINAL_SUBTITLE = "subtitle.srt"
    
    # 输出文件后缀定义
    CONVERSION_SUFFIXES = {
        "智能转换": "smart",
        "中文转英文": "cn_to_en", 
        "中文转中文": "cn_to_cn", 
        "英文转中文": "en_to_cn", 
        "英文转英文": "en_to_en"
    }
    
    # 临时文件前缀
    TEMP_PREFIX = "temp_"
    
    @staticmethod
    def normalize_path(path):
        """标准化路径格式"""
        return os.path.abspath(path).replace('\\', '/')
    
    @staticmethod
    def get_subtitle_filename(conversion_suffix):
        """获取字幕文件名"""
        return f"subtitle_{conversion_suffix}.srt"
    
    @staticmethod
    def get_output_video_filename(base_name, conversion_suffix):
        """获取输出视频文件名"""
        name, ext = os.path.splitext(base_name)
        return f"{name}_{conversion_suffix}{ext}"
    
    @staticmethod
    def get_temp_filename(base_name, suffix=""):
        """获取临时文件名"""
        return f"{PathConfig.TEMP_PREFIX}{base_name}{suffix}"
    
    @staticmethod
    def is_temp_file(filename):
        """判断是否为临时文件"""
        return filename.startswith(PathConfig.TEMP_PREFIX)
    
    @staticmethod
    def get_supported_video_extensions():
        """获取支持的视频文件扩展名"""
        return ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    
    @staticmethod
    def get_supported_audio_extensions():
        """获取支持的音频文件扩展名"""
        return ['.wav', '.mp3', '.aac', '.flac', '.ogg']
    
    @staticmethod
    def get_supported_subtitle_extensions():
        """获取支持的字幕文件扩展名"""
        return ['.srt', '.vtt', '.ass', '.ssa']

# 全局路径配置实例
path_config = PathConfig() 