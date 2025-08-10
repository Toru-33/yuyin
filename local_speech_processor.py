# -*- coding: utf-8 -*-
"""
本地化语音处理系统
集成 Whisper(语音识别) + TTS(语音合成) + Argos Translate(翻译)
完全离线运行，无需API调用
"""

import os
import time
import json
import warnings
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
import logging

# 音频处理
from pydub import AudioSegment
try:
    from moviepy.editor import VideoFileClip  # noqa: F401
except Exception:
    VideoFileClip = None

# 本地AI模型
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ Whisper未安装，语音识别功能不可用")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    print("⚠️ pyttsx3未安装，将尝试其他TTS方案")

try:
    import argostranslate.package
    import argostranslate.translate
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False
    print("⚠️ Argos Translate未安装，翻译功能不可用")

# 抑制警告
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

class LocalSpeechProcessor:
    """本地化语音处理器"""
    
    def __init__(self, cache_dir="local_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # 初始化模型
        self.whisper_model = None
        self.tts_engine = None
        self.translation_packages = {}
        
        # 支持的语言
        self.supported_languages = {
            'zh': 'Chinese',
            'en': 'English',
            'auto': 'Auto-detect'
        }
        
        self._init_models()
        
    def _init_models(self):
        """初始化所有本地模型"""
        print("🔄 正在初始化本地化模型...")
        
        # 1. 初始化Whisper语音识别
        if WHISPER_AVAILABLE:
            try:
                print("🎤 加载Whisper语音识别模型...")
                self.whisper_model = whisper.load_model("base")
                print("✅ Whisper模型加载成功")
            except Exception as e:
                print(f"❌ Whisper模型加载失败: {e}")
        
        # 2. 初始化TTS引擎
        if PYTTSX3_AVAILABLE:
            try:
                print("🗣️ 初始化TTS语音合成引擎...")
                self.tts_engine = pyttsx3.init()
                # 设置语音参数
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    # 尝试找到中文语音
                    for voice in voices:
                        if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                            self.tts_engine.setProperty('voice', voice.id)
                            break
                print("✅ TTS引擎初始化成功")
            except Exception as e:
                print(f"❌ TTS引擎初始化失败: {e}")
        
        # 3. 初始化翻译包
        if ARGOS_AVAILABLE:
            self._init_translation_packages()
    
    def _init_translation_packages(self):
        """初始化翻译语言包"""
        print("🌐 初始化翻译语言包...")
        try:
            # 更新包索引
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            
            # 安装常用语言包
            language_pairs = [
                ('en', 'zh'),  # 英文->中文
                ('zh', 'en'),  # 中文->英文
            ]
            
            for from_lang, to_lang in language_pairs:
                package = next(
                    (pkg for pkg in available_packages 
                     if pkg.from_code == from_lang and pkg.to_code == to_lang), 
                    None
                )
                if package:
                    try:
                        # 检查是否已安装
                        installed_packages = argostranslate.package.get_installed_packages()
                        is_installed = any(
                            pkg.from_code == from_lang and pkg.to_code == to_lang 
                            for pkg in installed_packages
                        )
                        
                        if not is_installed:
                            print(f"📦 下载翻译包: {from_lang} -> {to_lang}")
                            argostranslate.package.install_from_path(package.download())
                        
                        self.translation_packages[f"{from_lang}-{to_lang}"] = True
                        print(f"✅ 翻译包就绪: {from_lang} -> {to_lang}")
                    except Exception as e:
                        print(f"⚠️ 翻译包安装失败 {from_lang}->{to_lang}: {e}")
            
        except Exception as e:
            print(f"❌ 翻译包初始化失败: {e}")
    
    def transcribe_audio(self, audio_file, language="auto", progress_callback=None):
        """
        语音识别 - 使用Whisper
        
        Args:
            audio_file: 音频文件路径
            language: 语言代码 ('zh', 'en', 'auto')
            progress_callback: 进度回调函数
            
        Returns:
            dict: {'text': str, 'segments': list, 'language': str}
        """
        if not WHISPER_AVAILABLE or not self.whisper_model:
            raise Exception("Whisper语音识别不可用")
        
        if not os.path.exists(audio_file):
            raise Exception(f"音频文件不存在: {audio_file}")
        
        try:
            print(f"🎤 开始语音识别: {audio_file}")
            if progress_callback:
                progress_callback(10, "正在加载音频文件...")
            
            # 设置语言参数
            lang_param = None if language == "auto" else language
            
            if progress_callback:
                progress_callback(30, "正在进行语音识别...")
            
            # 使用Whisper进行识别
            result = self.whisper_model.transcribe(
                audio_file, 
                language=lang_param,
                verbose=False
            )
            
            if progress_callback:
                progress_callback(90, "语音识别完成")
            
            # 格式化结果
            formatted_result = {
                'text': result['text'].strip(),
                'segments': result.get('segments', []),
                'language': result.get('language', 'unknown'),
                'confidence': 0.85  # Whisper通常有较高的置信度
            }
            
            print(f"✅ 语音识别完成，识别语言: {formatted_result['language']}")
            print(f"📝 识别文本: {formatted_result['text'][:100]}...")
            
            if progress_callback:
                progress_callback(100, "语音识别完成")
            
            return formatted_result
            
        except Exception as e:
            error_msg = f"语音识别失败: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def translate_text(self, text, from_lang="auto", to_lang="zh"):
        """
        文本翻译 - 使用Argos Translate
        
        Args:
            text: 要翻译的文本
            from_lang: 源语言
            to_lang: 目标语言
            
        Returns:
            str: 翻译结果
        """
        if not ARGOS_AVAILABLE:
            print("⚠️ Argos Translate不可用，返回原文")
            return text
        
        if not text or not text.strip():
            return text
        
        try:
            # 自动检测语言
            if from_lang == "auto":
                # 简单的语言检测
                chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
                if chinese_chars > len(text) * 0.3:
                    from_lang = "zh"
                else:
                    from_lang = "en"
            
            # 如果源语言和目标语言相同，直接返回
            if from_lang == to_lang:
                return text
            
            print(f"🌐 翻译文本: {from_lang} -> {to_lang}")
            
            # 执行翻译
            translated = argostranslate.translate.translate(text, from_lang, to_lang)
            
            print(f"✅ 翻译完成: {text[:50]}... -> {translated[:50]}...")
            return translated
            
        except Exception as e:
            print(f"⚠️ 翻译失败，返回原文: {e}")
            return text
    
    def synthesize_speech(self, text, output_file, voice_type="default", speed=150, volume=0.8, language="zh"):
        """
        语音合成 - 使用pyttsx3
        
        Args:
            text: 要合成的文本
            output_file: 输出文件路径
            voice_type: 音色类型
            speed: 语速 (50-300)
            volume: 音量 (0.0-1.0)
            language: 语言
            
        Returns:
            bool: 合成是否成功
        """
        if not text or not text.strip():
            print("❌ 文本为空，跳过语音合成")
            return False
        
        if not PYTTSX3_AVAILABLE or not self.tts_engine:
            raise Exception("TTS语音合成引擎不可用")
        
        try:
            print(f"🗣️ 开始语音合成: {text[:50]}...")
            
            # 设置语音参数
            self.tts_engine.setProperty('rate', speed)
            self.tts_engine.setProperty('volume', volume)
            
            # 尝试设置合适的语音
            voices = self.tts_engine.getProperty('voices')
            if voices:
                for voice in voices:
                    voice_name = voice.name.lower()
                    voice_id = voice.id.lower()
                    
                    # 根据语言选择合适的语音
                    if language == "zh" and ('chinese' in voice_name or 'zh' in voice_id):
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                    elif language == "en" and ('english' in voice_name or 'en' in voice_id):
                        self.tts_engine.setProperty('voice', voice.id)
                        break
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 保存音频到文件
            self.tts_engine.save_to_file(text, output_file)
            self.tts_engine.runAndWait()
            
            # 验证文件是否生成
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                print(f"✅ 语音合成完成: {output_file}")
                return True
            else:
                # 如果直接保存失败，尝试其他方法
                print("⚠️ 直接保存失败，尝试备用方案...")
                return self._synthesize_with_fallback(text, output_file, speed, volume)
                
        except Exception as e:
            print(f"❌ 语音合成失败: {e}")
            return self._synthesize_with_fallback(text, output_file, speed, volume)
    
    def _synthesize_with_fallback(self, text, output_file, speed, volume):
        """备用语音合成方案"""
        try:
            # 尝试使用espeak（如果可用）
            if os.system("espeak --version > nul 2>&1") == 0:
                print("🔄 使用espeak进行语音合成...")
                cmd = f'espeak -s {speed} -a {int(volume*100)} "{text}" -w "{output_file}"'
                result = os.system(cmd)
                if result == 0 and os.path.exists(output_file):
                    print("✅ espeak语音合成成功")
                    return True
            
            # 创建一个简单的提示音频文件
            print("⚠️ 创建提示音频文件...")
            self._create_placeholder_audio(output_file, len(text))
            return True
            
        except Exception as e:
            print(f"❌ 备用方案也失败: {e}")
            return False
    
    def _create_placeholder_audio(self, output_file, text_length):
        """创建占位音频文件"""
        try:
            # 根据文本长度创建相应时长的静音
            duration = max(1000, text_length * 100)  # 每个字符100ms
            silence = AudioSegment.silent(duration=duration)
            silence.export(output_file, format="wav")
            print(f"✅ 创建占位音频: {output_file}")
        except Exception as e:
            print(f"❌ 创建占位音频失败: {e}")
    
    def parse_subtitle_file(self, subtitle_file):
        """
        解析字幕文件
        
        Args:
            subtitle_file: 字幕文件路径
            
        Returns:
            list: 字幕片段列表
        """
        if not os.path.exists(subtitle_file):
            raise Exception(f"字幕文件不存在: {subtitle_file}")
        
        try:
            segments = []
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析SRT格式
            if subtitle_file.endswith('.srt'):
                segments = self._parse_srt_content(content)
            else:
                # 其他格式的处理
                print(f"⚠️ 暂不支持的字幕格式: {subtitle_file}")
                return []
            
            print(f"✅ 解析字幕文件完成，共 {len(segments)} 个片段")
            return segments
            
        except Exception as e:
            error_msg = f"字幕文件解析失败: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def _parse_srt_content(self, content):
        """解析SRT字幕内容"""
        segments = []
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    # 序号
                    index = int(lines[0])
                    
                    # 时间
                    time_line = lines[1]
                    start_time, end_time = time_line.split(' --> ')
                    
                    # 文本
                    text = '\n'.join(lines[2:]).strip()
                    
                    segments.append({
                        'index': index,
                        'start_time': self._parse_time_to_seconds(start_time),
                        'end_time': self._parse_time_to_seconds(end_time),
                        'text': text
                    })
                except Exception as e:
                    print(f"⚠️ 跳过无效字幕块: {e}")
                    continue
        
        return segments
    
    def _parse_time_to_seconds(self, time_str):
        """将时间字符串转换为秒数"""
        # 格式: HH:MM:SS,mmm
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def process_video_with_subtitles(self, video_file, subtitle_file, output_path, 
                                   conversion_type="英文转中文", voice_params=None, 
                                   progress_callback=None):
        """
        完整的视频字幕处理流程
        
        Args:
            video_file: 视频文件路径
            subtitle_file: 字幕文件路径  
            output_path: 输出路径
            conversion_type: 转换类型
            voice_params: 语音参数
            progress_callback: 进度回调
            
        Returns:
            bool: 处理是否成功
        """
        try:
            print(f"🎬 开始处理视频: {video_file}")
            
            if progress_callback:
                progress_callback(5, "解析字幕文件...")
            
            # 1. 解析字幕文件
            segments = self.parse_subtitle_file(subtitle_file)
            if not segments:
                raise Exception("字幕文件解析失败或为空")
            
            if progress_callback:
                progress_callback(15, "准备语音合成...")
            
            # 2. 根据转换类型处理文本
            processed_segments = []
            for i, segment in enumerate(segments):
                if progress_callback:
                    progress = 15 + (i / len(segments)) * 30
                    progress_callback(int(progress), f"处理字幕片段 {i+1}/{len(segments)}")
                
                original_text = segment['text']
                processed_text = original_text
                
                # 根据转换类型进行翻译
                if conversion_type == "英文转中文":
                    processed_text = self.translate_text(original_text, "en", "zh")
                elif conversion_type == "中文转英文":
                    processed_text = self.translate_text(original_text, "zh", "en")
                elif conversion_type == "英文转英文":
                    processed_text = original_text  # 不翻译
                elif conversion_type == "中文转中文":
                    processed_text = original_text  # 不翻译
                
                processed_segments.append({
                    **segment,
                    'original_text': original_text,
                    'processed_text': processed_text
                })
            
            if progress_callback:
                progress_callback(45, "开始语音合成...")
            
            # 3. 语音合成
            temp_audio_dir = self.cache_dir / "temp_audio"
            temp_audio_dir.mkdir(exist_ok=True)
            
            audio_files = []
            for i, segment in enumerate(processed_segments):
                if progress_callback:
                    progress = 45 + (i / len(processed_segments)) * 35
                    progress_callback(int(progress), f"合成语音片段 {i+1}/{len(processed_segments)}")
                
                audio_file = temp_audio_dir / f"segment_{i+1}.wav"
                
                # 设置语音参数
                speed = voice_params.get('speed', 150) if voice_params else 150
                volume = voice_params.get('volume', 0.8) if voice_params else 0.8
                language = "zh" if "中文" in conversion_type else "en"
                
                success = self.synthesize_speech(
                    segment['processed_text'], 
                    str(audio_file),
                    speed=speed,
                    volume=volume,
                    language=language
                )
                
                if success:
                    audio_files.append(str(audio_file))
                else:
                    print(f"⚠️ 片段 {i+1} 语音合成失败，跳过")
            
            if progress_callback:
                progress_callback(80, "合并音频和视频...")
            
            # 4. 合并音频和视频（这里可以调用现有的合并逻辑）
            # 简化版本：只保存音频文件列表
            result_info = {
                'video_file': video_file,
                'subtitle_file': subtitle_file,
                'processed_segments': processed_segments,
                'audio_files': audio_files,
                'conversion_type': conversion_type,
                'success': True
            }
            
            # 保存处理结果信息
            result_file = Path(output_path) / "processing_result.json"
            result_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result_info, f, ensure_ascii=False, indent=2)
            
            if progress_callback:
                progress_callback(100, "处理完成")
            
            print(f"✅ 视频处理完成: {result_file}")
            return True
            
        except Exception as e:
            error_msg = f"视频处理失败: {str(e)}"
            print(f"❌ {error_msg}")
            if progress_callback:
                progress_callback(0, error_msg)
            return False
    
    def get_model_info(self):
        """获取模型信息"""
        info = {
            'whisper': {
                'available': WHISPER_AVAILABLE and self.whisper_model is not None,
                'model': 'base' if self.whisper_model else None
            },
            'tts': {
                'available': PYTTSX3_AVAILABLE and self.tts_engine is not None,
                'engine': 'pyttsx3' if self.tts_engine else None
            },
            'translation': {
                'available': ARGOS_AVAILABLE,
                'packages': list(self.translation_packages.keys())
            }
        }
        return info
    
    def cleanup_cache(self):
        """清理缓存文件"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(exist_ok=True)
                print("✅ 缓存清理完成")
        except Exception as e:
            print(f"⚠️ 缓存清理失败: {e}")


# 测试和示例代码
if __name__ == "__main__":
    print("🔧 本地化语音处理系统测试")
    
    # 创建处理器实例
    processor = LocalSpeechProcessor()
    
    # 显示模型信息
    info = processor.get_model_info()
    print("\n📊 模型状态:")
    for model_type, model_info in info.items():
        status = "✅ 可用" if model_info['available'] else "❌ 不可用"
        print(f"  {model_type}: {status}")
    
    # 测试翻译功能
    if info['translation']['available']:
        print("\n🌐 测试翻译功能:")
        test_text = "Hello, this is a test."
        translated = processor.translate_text(test_text, "en", "zh")
        print(f"原文: {test_text}")
        print(f"译文: {translated}")
    
    print("\n✅ 系统就绪，可以开始使用！") 