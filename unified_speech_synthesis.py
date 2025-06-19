#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一语音合成模块
整合了所有语音合成功能，改进了音频处理逻辑
解决了音调、衔接和代码重复问题
"""

import base64
import datetime
import hashlib
import hmac
import json
import os
import ssl
import threading
import time
import urllib.parse
import urllib.request
import uuid
import wave
import websocket
import requests
import random
from hashlib import md5
import re
import audiotsm
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
import numpy as np
from wsgiref.handlers import format_date_time
from time import mktime
import concurrent.futures
from queue import Queue


class UnifiedSpeechSynthesis:
    """统一语音合成类"""
    
    def __init__(self):
        self.synthesis_result = None
        self.synthesis_error = None
        self.synthesis_finished = False
        
        # 从配置文件加载API配置
        self.load_config()
        
        # 初始化音频缓存
        self.enable_cache = True  # 默认启用缓存
        self.cache_dir = "audio_cache"
        self._init_cache_dir()
        
    def load_config(self):
        """从config.json加载API配置"""
        try:
            print("🔧 正在加载API配置...")
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 讯飞语音合成API配置 - 使用专门的TTS密钥
                self.APPID = config.get('xunfei_tts_appid', 'dece0a1f')
                self.API_KEY = config.get('xunfei_tts_apikey', '5cc4877fa4b7d173d8f1c085e50a4788')
                self.API_SECRET = config.get('xunfei_tts_apisecret', 'Y2I4YTUxMDljZjk2YzAwZGMzNTgwYTNl')
                
                # 百度翻译API配置  
                self.BAIDU_APPID = config.get('baidu_appid', '20240510002047252')
                self.BAIDU_APPKEY = config.get('baidu_appkey', 'kTWYriLuEEEKr0BE70d1')
                
                print(f"✅ 成功加载语音合成API配置:")
                print(f"   TTS APPID: {self.APPID}")
                print(f"   TTS APIKey: {self.API_KEY[:8]}***")
                print(f"   TTS APISecret: {self.API_SECRET[:8]}***")
                print(f"   百度翻译APPID: {self.BAIDU_APPID}")
                print(f"   百度翻译APPKey: {self.BAIDU_APPKEY[:8]}***")
                
            else:
                print("⚠️ config.json文件不存在，使用默认API配置")
                # 使用语音合成的默认配置
                self.APPID = 'dece0a1f'
                self.API_KEY = '5cc4877fa4b7d173d8f1c085e50a4788'
                self.API_SECRET = 'Y2I4YTUxMDljZjk2YzAwZGMzNTgwYTNl'
                self.BAIDU_APPID = '20240510002047252'
                self.BAIDU_APPKEY = 'kTWYriLuEEEKr0BE70d1'
                
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            # 使用语音合成的默认配置
            self.APPID = 'dece0a1f'
            self.API_KEY = '5cc4877fa4b7d173d8f1c085e50a4788'
            self.API_SECRET = 'Y2I4YTUxMDljZjk2YzAwZGMzNTgwYTNl'
            self.BAIDU_APPID = '20240510002047252'
            self.BAIDU_APPKEY = 'kTWYriLuEEEKr0BE70d1'
    
    def create_websocket_url(self, text, voice_type="xiaoyan", speed=50, volume=50):
        """创建WebSocket连接URL - 使用正确的讯飞API认证方式（基于syntheticSpeech.py）"""
        from wsgiref.handlers import format_date_time
        from time import mktime
        from datetime import datetime
        from urllib.parse import urlencode
        
        # 使用正确的base URL (关键修复)
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        
        # 生成RFC1123格式的时间戳 (使用原来的正确方法)
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        # 拼接字符串 (完全按照原来的方法)
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.API_SECRET.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.API_KEY, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        

        
        return url
    
    def create_synthesis_params(self, text, voice_type="xiaoyan", speed=50, volume=50):
        """创建语音合成参数"""
        # 智能语音类型检测
        if self._is_chinese(text):
            if voice_type.startswith("x4_"):
                voice_type = "xiaoyan"  # 中文文本使用中文发音人
        else:
            if not voice_type.startswith("x4_"):
                voice_type = "x4_EnUs_Laura_education"  # 英文文本使用英文发音人
        
        # 优化语音参数
        adjusted_speed = self._adjust_speed_for_voice(speed, voice_type)
        adjusted_volume = self._adjust_volume_for_voice(volume, voice_type)
        adjusted_pitch = self._adjust_pitch_for_voice(voice_type, text)
        
        data = {
            "common": {
                "app_id": self.APPID
            },
            "business": {
                "aue": "lame",
                "auf": "audio/L16;rate=16000",
                "vcn": voice_type,
                "speed": adjusted_speed,
                "volume": adjusted_volume,
                "pitch": adjusted_pitch,  # 根据发音人和文本内容调整音调
                "bgs": 0,
                "tte": "UTF8"
            },
            "data": {
                "status": 2,
                "text": base64.b64encode(text.encode('utf-8')).decode('utf-8')
            }
        }
        return json.dumps(data)
    
    def _is_chinese(self, text):
        """检测文本是否包含中文"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def _adjust_speed_for_voice(self, speed, voice_type):
        """根据发音人调整语速"""
        if voice_type.startswith("x4_"):  # 英文发音人
            return max(35, min(speed - 5, 75))  # 英文稍慢一些，更自然
        else:  # 中文发音人
            # 针对不同中文发音人优化语速
            if voice_type in ["xiaoyan", "aisxping"]:
                return max(45, min(speed + 5, 85))  # 女声稍快一些
            elif voice_type in ["xiaoyu", "xiaofeng"]:
                return max(40, min(speed, 80))  # 男声保持中等
            else:
                return max(42, min(speed + 2, 82))
    
    def _adjust_volume_for_voice(self, volume, voice_type):
        """根据发音人调整音量"""
        if voice_type.startswith("x4_"):  # 英文发音人
            return max(65, min(volume + 3, 90))  # 英文稍大声一些
        else:  # 中文发音人
            # 针对不同中文发音人优化音量
            if voice_type in ["xiaoyan", "aisxping"]:
                return max(60, min(volume + 8, 92))  # 女声增加音量
            elif voice_type in ["xiaoyu", "xiaofeng"]:
                return max(55, min(volume + 5, 88))  # 男声适中
            else:
                return max(58, min(volume + 6, 90))
    
    def _adjust_pitch_for_voice(self, voice_type, text):
        """根据发音人和文本内容调整音调"""
        base_pitch = 50  # 基础音调
        
        if voice_type.startswith("x4_"):  # 英文发音人
            return max(45, min(base_pitch - 2, 55))  # 英文音调稍低
        else:  # 中文发音人
            # 根据文本长度和标点符号调整音调
            if '？' in text or '!' in text or '！' in text:
                # 疑问句和感叹句音调稍高
                pitch_adjust = 8
            elif '。' in text and len(text) > 20:
                # 长句音调稍低，更稳重
                pitch_adjust = -5
            elif len(text) < 10:
                # 短句音调稍高，更生动
                pitch_adjust = 5
            else:
                pitch_adjust = 0
            
            # 针对不同中文发音人优化音调
            if voice_type in ["xiaoyan", "aisxping"]:
                return max(48, min(base_pitch + 5 + pitch_adjust, 65))  # 女声音调稍高
            elif voice_type in ["xiaoyu", "xiaofeng"]:
                return max(42, min(base_pitch - 3 + pitch_adjust, 58))  # 男声音调稍低
            else:
                return max(45, min(base_pitch + pitch_adjust, 60))
    
    def synthesize_text(self, text, output_file, voice_type="xiaoyan", speed=50, volume=50, quality="高质量"):
        """使用讯飞语音合成API合成语音 - 增强缓存和质量支持"""
        if not text or not text.strip():
            print("❌ 文本为空，跳过合成")
            return False
        
        # 获取质量设置
        quality_settings = self._get_quality_settings(quality)
        
        # 检查缓存
        cache_key = self._get_cache_key(text.strip(), voice_type, speed, volume, quality)
        cached_file = self._get_cached_audio(cache_key)
        if cached_file:
            try:
                import shutil
                shutil.copy2(cached_file, output_file)
                print(f"✅ 使用缓存音频文件: {output_file}")
                return True
            except Exception as e:
                print(f"⚠️ 缓存文件复制失败: {e}")
        
        print(f"🎤 开始语音合成: {text[:50]}...")
        print(f"🎧 质量: {quality}, 采样率: {quality_settings['sample_rate']}Hz")
        
        self.synthesis_result = None
        self.synthesis_error = None
        self.synthesis_finished = False
        
        try:
            url = self.create_websocket_url(text, voice_type, speed, volume)
            params = self.create_synthesis_params(text, voice_type, speed, volume)
            
           
            
        except Exception as e:
            print(f"❌ 创建WebSocket URL失败: {e}")
            return False
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                code = data['code']
                
                if code != 0:
                    error_msg = data.get('message', '未知错误')
                    self.synthesis_error = f"语音合成API错误 (code: {code}): {error_msg}"
                    ws.close()
                    return
                
                audio_data = data.get('data', {}).get('audio')
                status = data.get('data', {}).get('status', 0)
                
                if audio_data:
                    decoded_audio = base64.b64decode(audio_data)
                    if self.synthesis_result is None:
                        self.synthesis_result = decoded_audio
                    else:
                        self.synthesis_result += decoded_audio
                
                if status == 2:
                    ws.close()
                    
            except Exception as e:
                self.synthesis_error = f"处理WebSocket消息时出错: {str(e)}"
                ws.close()
        
        def on_error(ws, error):
            self.synthesis_error = f"WebSocket连接错误: {str(error)}"
            
        def on_close(ws, close_status_code, close_msg):
            self.synthesis_finished = True
            
        def on_open(ws):
            try:
                ws.send(params)
            except Exception as e:
                self.synthesis_error = f"发送参数失败: {str(e)}"
                ws.close()
        
        try:
            # 创建并运行WebSocket连接
            websocket.enableTrace(False)
            ws = websocket.WebSocketApp(url,
                                      on_message=on_message,
                                      on_error=on_error,
                                      on_close=on_close)
            ws.on_open = on_open
            
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            
            # 等待合成完成
            timeout = 30
            start_time = time.time()
            
            while not self.synthesis_finished and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            if self.synthesis_error:
                raise Exception(self.synthesis_error)
            
            if self.synthesis_result is None:
                raise Exception("语音合成失败：未收到音频数据")
            
            # 保存音频文件
            temp_mp3_file = output_file.replace('.wav', '_temp.mp3')
            with open(temp_mp3_file, 'wb') as f:
                f.write(self.synthesis_result)
            
            # 验证并转换为WAV格式
            try:
                test_audio = AudioSegment.from_mp3(temp_mp3_file)
                audio = AudioSegment.from_mp3(temp_mp3_file)
                audio.export(output_file, format="wav")
                
                if os.path.exists(temp_mp3_file):
                    os.remove(temp_mp3_file)
                
            except Exception as e:
                # 尝试使用ffmpeg转换
                try:
                    import subprocess
                    cmd = ['ffmpeg', '-y', '-i', temp_mp3_file, '-ar', '16000', '-ac', '1', output_file]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        if os.path.exists(temp_mp3_file):
                            os.remove(temp_mp3_file)
                    else:
                        raise Exception(f"音频格式转换失败: {result.stderr}")
                except Exception:
                    # 最后尝试：重命名MP3为WAV
                    import shutil
                    shutil.move(temp_mp3_file, output_file)
            
            # 保存到缓存
            self._save_to_cache(cache_key, output_file)
            
            return True
            
        except Exception as e:
            raise
    
    def extract_original_audio_segments(self, video_file, segments, temp_audio_path=None, existing_audio_path=None):
        """从原视频中提取完整音频和间隔片段 - 支持使用已存在的音频文件"""
        try:
            import time
            import os
            
            # 如果提供了已存在的音频文件，直接使用
            if existing_audio_path and os.path.exists(existing_audio_path):
                print(f"🔄 使用已提取的音频文件: {existing_audio_path}")
                try:
                    full_original_audio = AudioSegment.from_wav(existing_audio_path)
                    print(f"✅ 已存在音频加载成功: {existing_audio_path}, 时长: {len(full_original_audio)/1000:.1f}秒")
                    return full_original_audio
                except Exception as load_error:
                    print(f"⚠️ 已存在音频文件加载失败，重新提取: {load_error}")
                    # 如果加载失败，继续执行下面的提取逻辑
            
            # 确保输出目录存在
            if temp_audio_path:
                os.makedirs(os.path.dirname(temp_audio_path), exist_ok=True)
                temp_full_audio = temp_audio_path
            else:
                temp_full_audio = f"temp_original_audio_{int(time.time())}.wav"
            
            print(f"正在从视频中提取原音频: {video_file} -> {temp_full_audio}")
            
            # 使用with语句确保视频对象正确关闭
            with VideoFileClip(video_file) as video:
                if video.audio is None:
                    print("⚠️ 警告：视频文件没有音频轨道")
                    return None
                
                # 添加错误处理和重试机制
                try:
                    # 使用MoviePy提取，移除不支持的temp_audiofile参数
                    video.audio.write_audiofile(
                        temp_full_audio,
                        verbose=False,
                        logger=None
                    )
                    
                except Exception as moviepy_error:
                    print(f"⚠️ MoviePy提取失败: {moviepy_error}")
                    
                    # 备用方案：使用ffmpeg直接提取，改善编码处理
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', video_file,
                        '-vn',  # 不处理视频
                        '-acodec', 'pcm_s16le',  # 16位PCM
                        '-ar', '44100',  # 使用原采样率
                        '-ac', '2',  # 保持立体声
                        temp_full_audio
                    ]
                    
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
                        if result.returncode != 0:
                            print(f"❌ ffmpeg提取音频失败:")
                            print(f"   返回码: {result.returncode}")
                            print(f"   错误信息: {result.stderr}")
                            
                            # 如果特定编码失败，尝试更通用的方法
                            print("🔄 尝试通用音频提取方法...")
                            cmd_generic = [
                                'ffmpeg', '-y',
                                '-i', video_file,
                                '-vn',
                                temp_full_audio
                            ]
                            
                            result2 = subprocess.run(cmd_generic, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
                            if result2.returncode != 0:
                                print(f"❌ 通用方法也失败: {result2.stderr}")
                                return None
                            else:
                                print("✅ 通用方法提取成功")
                        else:
                            print("✅ ffmpeg提取音频成功")
                            
                    except subprocess.TimeoutExpired:
                        print("❌ ffmpeg提取音频超时")
                        return None
                    except Exception as ffmpeg_error:
                        print(f"❌ ffmpeg执行出错: {ffmpeg_error}")
                        return None
            
            # 验证音频文件是否成功生成
            if not os.path.exists(temp_full_audio):
                print(f"❌ 音频文件生成失败: {temp_full_audio}")
                return None
                
            if os.path.getsize(temp_full_audio) == 0:
                print(f"❌ 音频文件为空: {temp_full_audio}")
                return None
            
            # 加载音频文件
            try:
                full_original_audio = AudioSegment.from_wav(temp_full_audio)
                print(f"✅ 原音频提取成功: {temp_full_audio}, 时长: {len(full_original_audio)/1000:.1f}秒")
            except Exception as load_error:
                print(f"❌ 音频文件加载失败: {load_error}")
                return None
            
            # 只有在使用默认路径时才立即清理
            if temp_audio_path is None and os.path.exists(temp_full_audio):
                try:
                    os.remove(temp_full_audio)
                    print(f"🗑️ 临时音频文件已清理: {temp_full_audio}")
                except Exception as cleanup_error:
                    print(f"⚠️ 清理临时文件失败: {cleanup_error}")
            
            return full_original_audio
            
        except Exception as e:
            print(f"❌ 提取原音频失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_smooth_transition(self, audio1, audio2, fade_duration=100):
        """在两个音频段之间创建平滑过渡"""
        if len(audio1) < fade_duration or len(audio2) < fade_duration:
            return audio1 + audio2
        
        # 对第一个音频的末尾进行淡出
        fade_out_audio = audio1[:-fade_duration] + audio1[-fade_duration:].fade_out(fade_duration)
        
        # 对第二个音频的开头进行淡入
        fade_in_audio = audio2[:fade_duration].fade_in(fade_duration) + audio2[fade_duration:]
        
        # 重叠混合过渡部分
        overlap = audio1[-fade_duration:].fade_out(fade_duration).overlay(
            audio2[:fade_duration].fade_in(fade_duration)
        )
        
        # 合并音频
        result = fade_out_audio[:-fade_duration] + overlap + fade_in_audio[fade_duration:]
        return result
    
    def merge_audio_with_original_intervals(self, synthesized_segments, segments, 
                                          original_audio_segments, total_duration, output_file):
        """使用原音频片段替代静音间隔合并音频 - 改进版"""
        try:
            # 创建基于原音频的完整背景音轨
            if original_audio_segments and isinstance(original_audio_segments, AudioSegment):
                # original_audio_segments 现在是完整的原音频
                full_original = original_audio_segments
                total_duration_ms = int(total_duration * 1000)
                
                # 确保原音频长度匹配
                if len(full_original) > total_duration_ms:
                    background_audio = full_original[:total_duration_ms]
                else:
                    # 如果原音频不够长，循环填充或用静音补齐
                    background_audio = full_original
                    while len(background_audio) < total_duration_ms:
                        remaining = total_duration_ms - len(background_audio)
                        if len(full_original) <= remaining:
                            background_audio += full_original
                        else:
                            background_audio += full_original[:remaining]
                
                # 降低背景音频音量（作为环境音）
                background_audio = background_audio - 25  # 降低25dB
                print(f"✅ 使用原视频音频作为背景，长度: {len(background_audio)/1000:.1f}秒")
            else:
                # 如果没有原音频，创建静音背景
                background_audio = AudioSegment.silent(duration=int(total_duration * 1000))
                print("⚠️ 原音频提取失败，使用静音作为背景。可能原因：")
                print("   1. 视频文件没有音频轨道")
                print("   2. 音频格式不支持")
                print("   3. 视频文件损坏")
                print("   💡 建议：检查原视频是否有音频，或尝试重新编码视频")
            
            # 在指定位置叠加合成语音
            final_audio = background_audio
            
            for i, ((text, start_time, end_time), synth_segment) in enumerate(zip(segments, synthesized_segments)):
                start_ms = int(start_time * 1000)
                end_ms = int(end_time * 1000)
                
                # 确保合成音频长度匹配时间间隔
                target_duration_ms = end_ms - start_ms
                if abs(len(synth_segment) - target_duration_ms) > 100:  # 100ms的容差
                    # 调整音频长度
                    speed_ratio = len(synth_segment) / target_duration_ms
                    if 0.8 < speed_ratio < 1.2:  # 只在合理范围内调整
                        # 使用简单的速度调整
                        synth_segment = synth_segment._spawn(synth_segment.raw_data, 
                                                          overrides={"frame_rate": int(synth_segment.frame_rate * speed_ratio)})
                        synth_segment = synth_segment.set_frame_rate(synth_segment.frame_rate)
                
                # 为合成音频添加渐变效果，改善衔接
                fade_duration = min(50, len(synth_segment) // 20)  # 最多50ms渐变
                if fade_duration > 10:
                    synth_segment = synth_segment.fade_in(fade_duration).fade_out(fade_duration)
                
                # 在语音段期间降低背景音量
                if start_ms < len(final_audio) and end_ms <= len(final_audio):
                    # 分割音频
                    before = final_audio[:start_ms]
                    during = final_audio[start_ms:end_ms] - 8  # 语音期间再降低8dB
                    after = final_audio[end_ms:]
                    
                    # 重新组合
                    final_audio = before + during + after
                
                # 叠加合成语音
                if start_ms < len(final_audio):
                    # 确保不超出边界
                    end_position = min(start_ms + len(synth_segment), len(final_audio))
                    if end_position > start_ms:
                        # 可能需要裁切synth_segment
                        if start_ms + len(synth_segment) > len(final_audio):
                            synth_segment = synth_segment[:len(final_audio) - start_ms]
                        
                        final_audio = final_audio.overlay(synth_segment, position=start_ms)
                
                print(f"✅ 片段 {i+1}: {start_time:.1f}s-{end_time:.1f}s 已叠加")
            
            # 导出最终音频
            final_audio.export(output_file, format="wav")
            print(f"✅ 音频合并完成: {output_file}, 总长度: {len(final_audio)/1000:.1f}秒")
            return final_audio
            
        except Exception as e:
            print(f"❌ 改进音频合并失败: {e}")
            # 备用方案：使用静音间隔
            return self._merge_with_silence(synthesized_segments, segments, total_duration, output_file)
    
    def _merge_with_silence(self, synthesized_segments, segments, total_duration, output_file):
        """备用方案：使用静音间隔合并音频"""
        merged_audio = AudioSegment.empty()
        
        for i, ((text, start_time, end_time), synth_segment) in enumerate(zip(segments, synthesized_segments)):
            # 添加前置间隔
            if i == 0 and start_time > 0:
                silence = AudioSegment.silent(duration=int(start_time * 1000))
                merged_audio += silence
            elif i > 0:
                previous_end_time = segments[i - 1][2]
                interval_duration = start_time - previous_end_time
                if interval_duration > 0:
                    silence = AudioSegment.silent(duration=int(interval_duration * 1000))
                    merged_audio += silence
            
            # 添加合成语音
            merged_audio += synth_segment
        
        # 导出音频
        merged_audio.export(output_file, format="wav")
        return merged_audio
    
    def adjust_audio_speed(self, audio_file, target_duration, output_file):
        """调整音频速度以匹配目标时长"""
        try:
            # 智能检测音频格式
            try:
                if audio_file.lower().endswith('.mp3'):
                    audio = AudioSegment.from_mp3(audio_file)
                elif audio_file.lower().endswith('.wav'):
                    audio = AudioSegment.from_wav(audio_file)
                else:
                    # 尝试自动检测
                    audio = AudioSegment.from_file(audio_file)
            except Exception as e:
                print(f"❌ 音频文件读取失败: {e}")
                return False
            
            current_duration = len(audio) / 1000.0
            speed_rate = current_duration / target_duration
            
            print(f"🎵 音频调速: 当前时长={current_duration:.2f}s, 目标时长={target_duration:.2f}s, 速度倍率={speed_rate:.2f}")
            
            if abs(speed_rate - 1.0) < 0.1:  # 如果速度差异小于10%，不调整
                print("⏭️ 速度差异小于10%，直接复制文件")
                audio.export(output_file, format="wav")
                return True
            
            # 改进的临时文件处理，避免占用冲突
            import uuid
            import time
            
            # 使用UUID和时间戳创建唯一的临时文件名
            unique_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time() * 1000)
            temp_wav_for_speed = f"temp_speed_{timestamp}_{unique_id}.wav"
            
            # 确保临时文件不存在
            if os.path.exists(temp_wav_for_speed):
                try:
                    os.remove(temp_wav_for_speed)
                except:
                    temp_wav_for_speed = f"temp_speed_{timestamp}_{unique_id}_2.wav"
            
            try:
                # 确保是WAV格式且符合audiotsm要求
                print(f"🎵 创建临时调速文件: {temp_wav_for_speed}")
                audio.set_frame_rate(16000).set_channels(1).export(temp_wav_for_speed, format="wav")
                
                # 等待文件系统完成写入
                time.sleep(0.1)
                
                # 验证临时文件
                if not os.path.exists(temp_wav_for_speed) or os.path.getsize(temp_wav_for_speed) == 0:
                    raise Exception("临时WAV文件创建失败")
                
                # 使用audiotsm进行高质量变速
                try:
                    reader = audiotsm.io.wav.WavReader(temp_wav_for_speed)
                    writer = audiotsm.io.wav.WavWriter(output_file, 1, 16000)
                    
                    # 使用WSOLA算法保持音质
                    wsola = audiotsm.wsola(1, speed=speed_rate)
                    wsola.run(reader, writer)
                    
                    # 确保读写器正确关闭
                    reader.close()
                    writer.close()
                    
                    print(f"✅ 使用audiotsm调速成功")
                    
                except Exception as audiotsm_exec_error:
                    print(f"⚠️ audiotsm执行失败: {audiotsm_exec_error}")
                    raise audiotsm_exec_error
                    
            except Exception as audiotsm_error:
                print(f"⚠️ audiotsm调速失败: {audiotsm_error}，尝试备用方法")
                
            finally:
                # 清理临时文件，添加多次尝试机制
                if os.path.exists(temp_wav_for_speed):
                    for attempt in range(3):
                        try:
                            time.sleep(0.1)  # 短暂等待，确保文件句柄释放
                            os.remove(temp_wav_for_speed)
                            print(f"🗑️ 临时调速文件已清理: {temp_wav_for_speed}")
                            break
                        except Exception as cleanup_error:
                            if attempt == 2:  # 最后一次尝试
                                print(f"⚠️ 清理临时文件失败 (尝试{attempt+1}/3): {cleanup_error}")
                                print(f"⚠️ 请手动删除文件: {temp_wav_for_speed}")
                            else:
                                time.sleep(0.2)  # 等待更长时间再试
            
            # 检查是否成功
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return True
                
                # 备用方法：使用pydub的简单速度调整
                try:
                    # 调整播放速度（改变帧率）
                    new_frame_rate = int(audio.frame_rate * speed_rate)
                    speed_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
                    speed_audio = speed_audio.set_frame_rate(16000)  # 重新设置为标准采样率
                    speed_audio.export(output_file, format="wav")
                    print(f"✅ 使用pydub调速成功")
                    return True
                except Exception as pydub_error:
                    print(f"❌ pydub调速也失败: {pydub_error}")
                    # 最后备用：直接复制原文件
                    audio.export(output_file, format="wav")
                    print(f"⚠️ 调速失败，使用原始音频")
                    return True
            
        except Exception as e:
            print(f"❌ 调整音频速度失败: {e}")
            return False
    
    def translate_text(self, text, from_lang='auto', to_lang='zh'):
        """翻译文本"""
        try:
            endpoint = 'http://api.fanyi.baidu.com'
            path = '/api/trans/vip/translate'
            url = endpoint + path
            
            def make_md5(s, encoding='utf-8'):
                return md5(s.encode(encoding)).hexdigest()
            
            salt = random.randint(32768, 65536)
            sign = make_md5(self.BAIDU_APPID + text + str(salt) + self.BAIDU_APPKEY)
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            payload = {
                'appid': self.BAIDU_APPID,
                'q': text,
                'from': from_lang,
                'to': to_lang,
                'salt': salt,
                'sign': sign
            }
            
            response = requests.post(url, params=payload, headers=headers, timeout=10)
            result = response.json()
            
            if 'trans_result' in result:
                return result['trans_result'][0]['dst']
            else:
                print(f"翻译失败: {result}")
                return text
                
        except Exception as e:
            print(f"翻译错误: {e}")
            return text
    
    def parse_subtitle_file(self, subtitle_file):
        """解析字幕文件"""
        segments = []
        
        # 读取字幕文件 - 支持多种编码
        subtitle_content = ""
        for encoding in ['utf-8', 'gbk', 'windows-1252', 'latin-1']:
            try:
                with open(subtitle_file, 'r', encoding=encoding) as f:
                    subtitle_content = f.read()
                print(f"✅ 成功使用 {encoding} 编码读取字幕文件")
                break
            except UnicodeDecodeError:
                continue
        
        if not subtitle_content:
            raise Exception("❌ 无法读取字幕文件")
        
        lines = subtitle_content.strip().split('\n')
        i = 0
        
        while i < len(lines):
            # 跳过空行
            while i < len(lines) and not lines[i].strip():
                i += 1
            
            if i >= len(lines):
                break
            
            # 检查序号行
            if i < len(lines) and lines[i].strip().isdigit():
                i += 1
                
                # 读取时间行
                if i < len(lines) and "-->" in lines[i]:
                    time_line = lines[i].strip()
                    i += 1
                    
                    # 读取文本行
                    text_lines = []
                    while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    if text_lines:
                        text = ' '.join(text_lines).strip()
                        text = self._clean_subtitle_text(text)
                        
                        if text and len(text) > 1:
                            # 解析时间
                            time_parts = time_line.split(" --> ")
                            if len(time_parts) == 2:
                                start_time = self._parse_time(time_parts[0])
                                end_time = self._parse_time(time_parts[1])
                                
                                if start_time is not None and end_time is not None:
                                    segments.append((text, start_time, end_time))
            else:
                i += 1
        
        return segments
    
    def _parse_time(self, time_str):
        """解析时间字符串为秒数"""
        try:
            time_pattern = r'(\d{2}):(\d{2}):(\d{1,2})[,.](\d{1,3})'
            match = re.search(time_pattern, time_str)
            
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                milliseconds = int(match.group(4).ljust(3, '0')[:3])
                
                return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            return None
        except:
            return None
    
    def _clean_subtitle_text(self, text):
        """清理字幕文本"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除特殊字符
        text = re.sub(r'[♪♫♬♩]', '', text)
        # 移除多余空格
        text = ' '.join(text.split())
        return text.strip()
    
    def process_video(self, video_file, subtitle_file, output_path, 
                     conversion_type="英文转英文", voice_type=None, speed=100, volume=80,
                     progress_callback=None, existing_audio_path=None, quality="高质量"):
        """
        处理视频：合成语音并替换音频
        
        Args:
            video_file: 视频文件路径 
            subtitle_file: 字幕文件路径
            output_path: 输出视频路径
            conversion_type: 转换类型
            voice_type: 发音人类型
            speed: 语速
            volume: 音量
            progress_callback: 进度回调函数
            existing_audio_path: 已存在的音频文件路径（避免重复提取）
            quality: 输出质量 ("标准质量", "高质量", "超清质量")
        
        Returns:
            str: 生成的视频文件路径
        """
        try:
            import time
            import os
            from pydub import AudioSegment
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"视频文件不存在: {video_file}")
            
            if not os.path.exists(subtitle_file):
                raise FileNotFoundError(f"字幕文件不存在: {subtitle_file}")
            
            print(f"🎬 开始处理视频: {video_file}")
            print(f"📝 字幕文件: {subtitle_file}")
            print(f"🎯 转换类型: {conversion_type}")
            print(f"🗣️ 发音人: {voice_type}")
            print(f"🎧 输出质量: {quality}")
            
            # 根据质量设置调整音频参数
            quality_settings = self._get_quality_settings(quality)
            
            if progress_callback:
                progress_callback(10, "解析字幕文件...")
            
            # 解析字幕文件
            segments = self.parse_subtitle_file(subtitle_file)
            if not segments:
                raise Exception("字幕文件解析失败或为空")
            
            print(f"📄 解析到 {len(segments)} 个字幕段落")
            
            # 创建临时目录
            import tempfile
            temp_dir = tempfile.mkdtemp(prefix="speech_synthesis_")
            
            def get_temp_path(filename):
                return os.path.join(temp_dir, filename).replace('\\', '/')
            
            # 获取视频总时长
            try:
                video = VideoFileClip(video_file)
                total_duration = video.duration
                video.close()
            except Exception as e:
                print(f"获取视频时长失败: {e}")
                # 使用最后一个字幕的结束时间作为总时长
                total_duration = segments[-1][2] + 1
            
            # 合成语音
            synthesized_segments = []
            temp_files = []  # 跟踪所有临时文件
            
            # 提取原音频片段（用于间隔）- 使用已存在的音频文件
            if progress_callback:
                progress_callback(20, "处理原音频片段...")
            original_audio_path = get_temp_path("original_audio.wav")
            temp_files.append(original_audio_path)
            original_audio_segments = self.extract_original_audio_segments(
                video_file, segments, original_audio_path, existing_audio_path
            )
            
            # 预处理所有文本（翻译）
            if progress_callback:
                progress_callback(25, "预处理字幕文本...")
            
            processed_segments = []
            for i, (text, start_time, end_time) in enumerate(segments):
                # 根据转换类型处理文本
                if conversion_type == "中文转英文":
                    processed_text = self.translate_text(text, 'zh', 'en')
                    default_voice = voice_type or "x4_EnUs_Laura_education"
                elif conversion_type == "英文转中文":
                    processed_text = self.translate_text(text, 'en', 'zh')
                    default_voice = voice_type or "xiaoyan"
                elif conversion_type == "中文转中文":
                    processed_text = text
                    default_voice = voice_type or "xiaoyan"
                else:  # 英文转英文
                    processed_text = text
                    default_voice = voice_type or "x4_EnUs_Laura_education"
                
                processed_segments.append((processed_text, start_time, end_time))
                
                if progress_callback and i % 5 == 0:  # 每5个更新一次进度
                    progress = 25 + int((i / len(segments)) * 15)
                    progress_callback(progress, f"预处理文本 {i+1}/{len(segments)}")
            
            # 🚀 使用批量合成大幅提高速度
            if progress_callback:
                progress_callback(40, "开始批量语音合成...")
            
            def batch_progress_callback(progress, message):
                if progress_callback:
                    # 批量合成占40%进度（从40%到80%）
                    actual_progress = 40 + int(progress * 0.4)
                    progress_callback(actual_progress, message)
            
            # 确保发音人参数正确传递
            actual_voice = voice_type or default_voice
            print(f"🎤 使用发音人: {actual_voice}")
            print(f"🎧 音频质量: {quality}")
            
            synthesized_segments = self.synthesize_batch_segments(
                processed_segments, actual_voice, speed, volume, batch_progress_callback, quality
            )
            
            # 合并音频 - 使用统一的路径
            if progress_callback:
                progress_callback(85, "合并音频...")
            
            merged_audio_file = get_temp_path("merged_audio.wav")
            temp_files.append(merged_audio_file)
            
            self.merge_audio_with_original_intervals(
                synthesized_segments, segments, original_audio_segments, 
                total_duration, merged_audio_file
            )
            
            # 合并视频和新音频
            if progress_callback:
                progress_callback(95, "合并视频和音频...")
            
            try:
                print(f"🎬 开始合并视频和音频...")
                print(f"   视频文件: {video_file}")
                print(f"   音频文件: {merged_audio_file}")
                print(f"   输出文件: {output_path}")
                
                # 检查音频文件是否存在且有效
                if not os.path.exists(merged_audio_file):
                    raise Exception(f"合成音频文件不存在: {merged_audio_file}")
                
                audio_size = os.path.getsize(merged_audio_file)
                if audio_size == 0:
                    raise Exception(f"合成音频文件为空: {merged_audio_file}")
                
                print(f"   音频文件大小: {audio_size / (1024*1024):.2f} MB")
                
                # 使用FFmpeg直接合并（更可靠）
                try:
                    import subprocess
                    
                    # FFmpeg命令：替换视频中的音频
                    ffmpeg_cmd = [
                        "ffmpeg", "-y",  # 覆盖输出文件
                        "-i", video_file,  # 输入视频
                        "-i", merged_audio_file,  # 输入音频
                        "-c:v", "copy",  # 复制视频流（不重编码）
                        "-c:a", "aac",   # 音频编码为AAC
                        "-strict", "experimental",
                        "-map", "0:v:0",  # 使用第一个文件的视频流
                        "-map", "1:a:0",  # 使用第二个文件的音频流
                        "-shortest",      # 以最短的流为准
                        output_path
                    ]
                    
                    print(f"🔧 执行FFmpeg命令: {' '.join(ffmpeg_cmd)}")
                    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, encoding='utf-8')
                    
                    if result.returncode == 0:
                        print(f"✅ FFmpeg合并成功!")
                        
                        # 验证输出文件
                        if os.path.exists(output_path):
                            output_size = os.path.getsize(output_path)
                            print(f"   输出文件大小: {output_size / (1024*1024):.2f} MB")
                        else:
                            raise Exception("输出文件未生成")
                    else:
                        print(f"❌ FFmpeg错误: {result.stderr}")
                        raise Exception(f"FFmpeg合并失败: {result.stderr}")
                        
                except Exception as ffmpeg_error:
                    print(f"⚠️ FFmpeg合并失败，尝试MoviePy方案: {ffmpeg_error}")
                    
                    # 备用方案：使用MoviePy
                    video = VideoFileClip(video_file)
                    new_audio = AudioSegment.from_wav(merged_audio_file)
                    
                    # 将AudioSegment转换为moviepy可用的音频
                    temp_audio_file = get_temp_path("final_audio.wav")
                    temp_files.append(temp_audio_file)
                    new_audio.export(temp_audio_file, format="wav")
                    
                    from moviepy.editor import AudioFileClip
                    new_audio_clip = AudioFileClip(temp_audio_file)
                    
                    print(f"📊 视频时长: {video.duration:.1f}s, 音频时长: {new_audio_clip.duration:.1f}s")
                    
                    # 确保音频时长匹配视频
                    if new_audio_clip.duration > video.duration:
                        print(f"🔧 裁剪音频: {new_audio_clip.duration:.1f}s -> {video.duration:.1f}s")
                        new_audio_clip = new_audio_clip.subclip(0, video.duration)
                    elif new_audio_clip.duration < video.duration:
                        # 如果音频较短，在末尾添加静音
                        silence_duration = video.duration - new_audio_clip.duration
                        print(f"🔧 添加静音: {silence_duration:.1f}s")
                        silence = AudioSegment.silent(duration=int(silence_duration * 1000))
                        extended_audio = new_audio + silence
                        extended_temp_file = get_temp_path("extended_audio.wav")
                        temp_files.append(extended_temp_file)
                        extended_audio.export(extended_temp_file, format="wav")
                        new_audio_clip.close()
                        new_audio_clip = AudioFileClip(extended_temp_file)
                    
                    final_video = video.set_audio(new_audio_clip)
                    final_video.write_videofile(
                        output_path, 
                        codec='libx264', 
                        audio_codec='aac',
                        temp_audiofile=get_temp_path("temp_audio.m4a"),
                        remove_temp=True,
                        verbose=False, 
                        logger=None
                    )
                    
                    # 清理资源
                    video.close()
                    new_audio_clip.close()
                    final_video.close()
                    
                    print(f"✅ MoviePy合并成功!")
                
                # 最终验证
                if os.path.exists(output_path):
                    final_size = os.path.getsize(output_path)
                    print(f"✅ 视频处理成功: {output_path}")
                    print(f"   最终文件大小: {final_size / (1024*1024):.2f} MB")
                    
                    # 使用FFprobe检查音频轨道
                    try:
                        probe_cmd = ["ffprobe", "-v", "quiet", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", output_path]
                        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
                        if probe_result.returncode == 0 and probe_result.stdout.strip():
                            print(f"✅ 音频轨道验证: {probe_result.stdout.strip()}")
                        else:
                            print(f"⚠️ 音频轨道检查失败")
                    except:
                        print(f"⚠️ 无法验证音频轨道（ffprobe不可用）")
                else:
                    raise Exception("输出文件不存在")
                    
            except Exception as e:
                print(f"❌ 合并视频音频失败: {e}")
                # 至少保存音频文件到输出目录
                backup_audio = output_path.replace('.mp4', '_audio.wav')
                import shutil
                shutil.copy2(merged_audio_file, backup_audio)
                print(f"⚠️ 已保存音频文件: {backup_audio}")
                raise e
            
            # 清理所有临时文件和目录
            cleanup_count = 0
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                        cleanup_count += 1
                except Exception as e:
                    print(f"⚠️ 清理临时文件失败 {temp_file}: {e}")
            
            # 清理临时目录
            try:
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
                    print(f"🗑️ 已清理临时目录: {temp_dir}")
                else:
                    print(f"⚠️ 临时目录非空，保留: {temp_dir}")
            except Exception as e:
                print(f"⚠️ 清理临时目录失败: {e}")
            
            print(f"🧹 临时文件清理完成，共清理 {cleanup_count} 个文件")
            
            if progress_callback:
                progress_callback(100, "处理完成")
            
            return output_path
            
        except Exception as e:
            print(f"❌ 处理视频失败: {e}")
            
            # 出错时也尝试清理临时文件
            try:
                if 'temp_files' in locals():
                    for temp_file in temp_files:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                if 'temp_dir' in locals() and os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"🗑️ 错误清理: 已删除临时目录 {temp_dir}")
            except Exception as cleanup_error:
                print(f"⚠️ 错误清理失败: {cleanup_error}")
                
            raise e
    
    def synthesize_batch_segments(self, text_segments, voice_type="xiaoyan", speed=50, volume=50, progress_callback=None, quality="高质量"):
        """批量合成音频片段，使用并行处理提高速度"""
        print(f"🚀 开始批量合成 {len(text_segments)} 个音频片段...")
        
        # 创建结果队列，保持顺序
        results = [None] * len(text_segments)
        failed_indices = []
        
        # 串行处理所有文本片段
        for i, (text, start_time, end_time) in enumerate(text_segments):
            if not text.strip():
                continue
                
            try:
                temp_output = f"temp_segment_{i}_{int(time.time() * 1000)}.wav"
                
                # 调用原有的合成方法
                success = self.synthesize_text(text, temp_output, voice_type, speed, volume, quality)
                
                if success and os.path.exists(temp_output):
                    # 读取音频数据到内存
                    audio_segment = AudioSegment.from_wav(temp_output)
                    results[i] = audio_segment
                    
                    # 立即清理临时文件
                    try:
                        os.remove(temp_output)
                    except:
                        pass
                else:
                    failed_indices.append(i)
                    
            except Exception as e:
                print(f"❌ 片段 {i} 合成失败: {e}")
                failed_indices.append(i)
            
            # 更新进度
            if progress_callback:
                progress = int(((i + 1) / len(text_segments)) * 30)  # 合成占30%进度
                progress_callback(progress, f"已完成音频合成 {i + 1}/{len(text_segments)}")
        
        # 重试失败的片段（串行）
        if failed_indices:
            print(f"⚠️ 重试 {len(failed_indices)} 个失败的片段...")
            for index in failed_indices:
                if index < len(text_segments):
                    text, start_time, end_time = text_segments[index]
                    temp_output = f"temp_retry_{index}_{int(time.time() * 1000)}.wav"
                    
                    print(f"🔄 重试片段 {index}: {text[:50]}... (使用发音人: {voice_type})")
                    
                    try:
                        # 增加重试次数和等待时间
                        success = False
                        for attempt in range(3):  # 最多3次重试
                            success = self.synthesize_text(text, temp_output, voice_type, speed, volume, quality)
                            if success and os.path.exists(temp_output) and os.path.getsize(temp_output) > 0:
                                results[index] = AudioSegment.from_wav(temp_output)
                                os.remove(temp_output)
                                print(f"✅ 片段 {index} 重试成功 (第{attempt+1}次)")
                                break
                            else:
                                print(f"⚠️ 片段 {index} 第{attempt+1}次重试失败")
                                if attempt < 2:  # 不是最后一次，等待重试
                                    time.sleep(1)
                        
                        if not success:
                            print(f"❌ 片段 {index} 所有重试都失败，使用静音")
                            results[index] = AudioSegment.silent(duration=int((end_time - start_time) * 1000))
                            
                    except Exception as e:
                        print(f"❌ 片段 {index} 重试异常: {e}")
                        results[index] = AudioSegment.silent(duration=int((end_time - start_time) * 1000))
        
        print(f"✅ 批量合成完成，成功率: {(len(text_segments) - len(failed_indices))/len(text_segments)*100:.1f}%")
        return results
    
    def _init_cache_dir(self):
        """初始化音频缓存目录"""
        try:
            import os
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
            print(f"🗂️ 音频缓存目录: {self.cache_dir}")
        except Exception as e:
            print(f"⚠️ 创建缓存目录失败: {e}")
            self.enable_cache = False
    
    def _get_quality_settings(self, quality):
        """根据质量设置获取音频参数"""
        quality_map = {
            "标准质量": {
                "sample_rate": 16000,
                "bitrate": "128k",
                "audio_format": "mp3",
                "fade_duration": 50,
                "compression": "medium"
            },
            "高质量": {
                "sample_rate": 22050,
                "bitrate": "192k", 
                "audio_format": "wav",
                "fade_duration": 100,
                "compression": "low"
            },
            "超清质量": {
                "sample_rate": 44100,
                "bitrate": "320k",
                "audio_format": "wav",
                "fade_duration": 150,
                "compression": "none"
            }
        }
        return quality_map.get(quality, quality_map["高质量"])
    
    def _get_cache_key(self, text, voice_type, speed, volume, quality):
        """生成缓存键值"""
        import hashlib
        cache_string = f"{text}_{voice_type}_{speed}_{volume}_{quality}"
        return hashlib.md5(cache_string.encode('utf-8')).hexdigest()
    
    def _get_cached_audio(self, cache_key):
        """从缓存获取音频文件"""
        if not self.enable_cache:
            return None
            
        try:
            import os
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
            if os.path.exists(cache_file):
                print(f"🎯 使用缓存音频: {cache_key}")
                return cache_file
        except Exception as e:
            print(f"⚠️ 读取缓存失败: {e}")
        return None
    
    def _save_to_cache(self, cache_key, audio_file):
        """保存音频到缓存"""
        if not self.enable_cache:
            return
            
        try:
            import os
            import shutil
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.wav")
            shutil.copy2(audio_file, cache_file)
            print(f"💾 音频已缓存: {cache_key}")
        except Exception as e:
            print(f"⚠️ 保存缓存失败: {e}")
    
    def set_cache_enabled(self, enabled):
        """设置是否启用缓存"""
        self.enable_cache = enabled
        if enabled:
            self._init_cache_dir()
        print(f"🗂️ 音频缓存: {'启用' if enabled else '禁用'}")


# 向后兼容的函数接口
def run(video_file, subtitle_file, output_path, voice_type="xiaoyan", speed=100, volume=80):
    """向后兼容的接口 - 中文转中文"""
    synthesis = UnifiedSpeechSynthesis()
    return synthesis.process_video(
        video_file, subtitle_file, output_path,
        conversion_type="中文转中文", voice_type=voice_type, speed=speed, volume=volume
    )


# 为不同转换类型提供的便捷函数
def run_cn_to_en(video_file, subtitle_file, output_path, voice_type="x4_EnUs_Laura_education", speed=100, volume=80):
    """中文转英文"""
    synthesis = UnifiedSpeechSynthesis()
    return synthesis.process_video(
        video_file, subtitle_file, output_path,
        conversion_type="中文转英文", voice_type=voice_type, speed=speed, volume=volume
    )


def run_en_to_cn(video_file, subtitle_file, output_path, voice_type="xiaoyan", speed=100, volume=80):
    """英文转中文"""
    synthesis = UnifiedSpeechSynthesis()
    return synthesis.process_video(
        video_file, subtitle_file, output_path,
        conversion_type="英文转中文", voice_type=voice_type, speed=speed, volume=volume
    )


def run_en_to_en(video_file, subtitle_file, output_path, voice_type="x4_EnUs_Laura_education", speed=100, volume=80):
    """英文转英文"""
    synthesis = UnifiedSpeechSynthesis()
    return synthesis.process_video(
        video_file, subtitle_file, output_path,
        conversion_type="英文转英文", voice_type=voice_type, speed=speed, volume=volume
    )


if __name__ == "__main__":
    # 测试代码
    synthesis = UnifiedSpeechSynthesis()
    print("统一语音合成模块已就绪") 