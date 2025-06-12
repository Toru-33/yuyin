# -*- coding: utf-8 -*-
"""
增强版语音合成模块
支持更多参数配置、缓存机制、错误恢复等功能
"""

import os
import json
import hashlib
import threading
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

import audiotsm
import audiotsm.io.wav
import subprocess
import re
import websocket
import datetime
import base64
import hmac
import ssl
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread

from pydub import AudioSegment
import config_manager

@dataclass
class VoiceConfig:
    """语音配置类"""
    voice_name: str = "xiaoyan"  # 发音人
    speed: int = 100  # 语速 (50-200)
    volume: int = 80  # 音量 (0-100)
    pitch: int = 50   # 音调 (0-100)
    audio_format: str = "lame"  # 音频格式
    sample_rate: int = 16000  # 采样率

@dataclass
class SynthesisTask:
    """合成任务类"""
    text: str
    start_time: float
    end_time: float
    index: int
    voice_config: VoiceConfig

class AudioCache:
    """音频缓存管理"""
    
    def __init__(self, cache_dir: str = "audio_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_index = self._load_cache_index()
    
    def _load_cache_index(self) -> Dict[str, str]:
        """加载缓存索引"""
        index_file = self.cache_dir / "cache_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_cache_index(self):
        """保存缓存索引"""
        index_file = self.cache_dir / "cache_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
    
    def _get_cache_key(self, text: str, voice_config: VoiceConfig) -> str:
        """生成缓存键"""
        config_str = f"{voice_config.voice_name}_{voice_config.speed}_{voice_config.volume}_{voice_config.pitch}"
        content = f"{text}_{config_str}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_cached_audio(self, text: str, voice_config: VoiceConfig) -> Optional[str]:
        """获取缓存的音频文件"""
        cache_key = self._get_cache_key(text, voice_config)
        if cache_key in self.cache_index:
            cache_file = self.cache_dir / self.cache_index[cache_key]
            if cache_file.exists():
                return str(cache_file)
        return None
    
    def cache_audio(self, text: str, voice_config: VoiceConfig, audio_file: str) -> str:
        """缓存音频文件"""
        cache_key = self._get_cache_key(text, voice_config)
        cache_filename = f"{cache_key}.wav"
        cache_file = self.cache_dir / cache_filename
        
        # 复制音频文件到缓存目录
        if os.path.exists(audio_file):
            import shutil
            shutil.copy2(audio_file, cache_file)
            
            # 更新缓存索引
            self.cache_index[cache_key] = cache_filename
            self._save_cache_index()
            
            return str(cache_file)
        return audio_file
    
    def clear_cache(self):
        """清空缓存"""
        for file in self.cache_dir.glob("*.wav"):
            file.unlink()
        self.cache_index.clear()
        self._save_cache_index()

class EnhancedSpeechSynthesis:
    """增强版语音合成器"""
    
    def __init__(self):
        self.cache = AudioCache()
        self.api_config = config_manager.get_xunfei_config()
        self.voice_config = VoiceConfig()
        self.load_voice_config()
        
    def load_voice_config(self):
        """加载语音配置"""
        voice_config = config_manager.get_voice_config()
        self.voice_config.speed = voice_config.get('speed', 100)
        self.voice_config.volume = voice_config.get('volume', 80)
        self.voice_config.voice_name = voice_config.get('voice_type', 'xiaoyan')
    
    def update_api_config(self, appid: str, api_key: str, api_secret: str):
        """更新API配置"""
        self.api_config = {
            'appid': appid,
            'api_key': api_key,
            'api_secret': api_secret
        }
    
    def create_websocket_url(self, text: str) -> str:
        """创建WebSocket连接URL"""
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        
        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(
            self.api_config['api_secret'].encode('utf-8'), 
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
        
        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.api_config['api_key'], "hmac-sha256", "host date request-line", signature_sha)
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
    
    def synthesize_text(self, text: str, output_file: str) -> bool:
        """合成单段文本"""
        # 检查缓存
        cached_file = self.cache.get_cached_audio(text, self.voice_config)
        if cached_file:
            # 复制缓存文件
            import shutil
            shutil.copy2(cached_file, output_file)
            return True
        
        # 执行合成
        success = self._do_synthesis(text, output_file)
        
        # 缓存结果
        if success:
            self.cache.cache_audio(text, self.voice_config, output_file)
        
        return success
    
    def _do_synthesis(self, text: str, output_file: str) -> bool:
        """执行实际的语音合成"""
        try:
            # 创建WebSocket参数
            ws_param = self._create_ws_param(text)
            
            # 建立WebSocket连接
            ws_url = self.create_websocket_url(text)
            
            # 创建临时文件来接收音频数据
            temp_mp3_file = "temp_synthesis.mp3"
            if os.path.exists(temp_mp3_file):
                os.remove(temp_mp3_file)
            
            # 设置回调函数
            synthesis_completed = threading.Event()
            synthesis_success = [False]
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    code = data["code"]
                    
                    if code != 0:
                        print(f"合成错误: {data.get('message', '未知错误')}")
                        synthesis_completed.set()
                        return
                    
                    audio = data["data"]["audio"]
                    audio_data = base64.b64decode(audio)
                    status = data["data"]["status"]
                    
                    # 写入音频数据
                    with open(temp_mp3_file, 'ab') as f:
                        f.write(audio_data)
                    
                    if status == 2:  # 合成完成
                        synthesis_success[0] = True
                        synthesis_completed.set()
                        ws.close()
                        
                except Exception as e:
                    print(f"处理消息异常: {e}")
                    synthesis_completed.set()
            
            def on_error(ws, error):
                print(f"WebSocket错误: {error}")
                synthesis_completed.set()
            
            def on_close(ws, close_status_code, close_msg):
                synthesis_completed.set()
            
            def on_open(ws):
                def run(*args):
                    d = {
                        "common": ws_param['common'],
                        "business": ws_param['business'],
                        "data": ws_param['data'],
                    }
                    ws.send(json.dumps(d))
                
                thread.start_new_thread(run, ())
            
            # 创建WebSocket连接
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # 启动连接
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            
            # 等待合成完成
            synthesis_completed.wait(timeout=30)
            
            if synthesis_success[0] and os.path.exists(temp_mp3_file):
                # 转换格式
                cmd = f'ffmpeg -y -i {temp_mp3_file} {output_file}'
                result = subprocess.run(cmd, shell=True, capture_output=True)
                
                # 清理临时文件
                if os.path.exists(temp_mp3_file):
                    os.remove(temp_mp3_file)
                
                return result.returncode == 0
            
            return False
            
        except Exception as e:
            print(f"语音合成异常: {e}")
            return False
    
    def _create_ws_param(self, text: str) -> Dict:
        """创建WebSocket参数"""
        # 根据语言选择合适的发音人
        voice_name = self._get_voice_name(text)
        
        return {
            "common": {"app_id": self.api_config['appid']},
            "business": {
                "aue": self.voice_config.audio_format,
                "auf": f"audio/L16;rate={self.voice_config.sample_rate}",
                "vcn": voice_name,
                "tte": "utf8",
                "speed": self._convert_speed(self.voice_config.speed),
                "volume": self._convert_volume(self.voice_config.volume),
                "pitch": self._convert_pitch(self.voice_config.pitch)
            },
            "data": {
                "status": 2,
                "text": str(base64.b64encode(text.encode('utf-8')), "UTF8")
            }
        }
    
    def _get_voice_name(self, text: str) -> str:
        """根据文本内容选择合适的发音人"""
        # 简单的语言检测
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if chinese_chars > english_chars:
            # 中文发音人
            voice_map = {
                "xiaoyan": "xiaoyan",
                "xiaoyu": "xiaoyu", 
                "xiaoxin": "xiaoxin"
            }
        else:
            # 英文发音人
            voice_map = {
                "xiaoyan": "x4_EnUs_Laura_education",
                "xiaoyu": "x4_EnUs_Emma_education",
                "xiaoxin": "x4_EnUs_Alex_education"
            }
        
        return voice_map.get(self.voice_config.voice_name, "xiaoyan")
    
    def _convert_speed(self, speed: int) -> int:
        """转换语速参数 (50-200 -> 0-100)"""
        return max(0, min(100, int((speed - 50) * 100 / 150)))
    
    def _convert_volume(self, volume: int) -> int:
        """转换音量参数 (0-100 -> 0-100)"""
        return max(0, min(100, volume))
    
    def _convert_pitch(self, pitch: int) -> int:
        """转换音调参数 (0-100 -> 0-100)"""
        return max(0, min(100, pitch))
    
    def adjust_audio_speed(self, audio_file: str, target_duration: float, output_file: str) -> bool:
        """调整音频速度以匹配目标时长"""
        try:
            # 获取原音频时长
            audio = AudioSegment.from_file(audio_file)
            original_duration = audio.duration_seconds
            
            if original_duration <= 0:
                return False
            
            # 计算速度倍率
            speed_ratio = original_duration / target_duration
            
            # 使用audiotsm调整速度
            reader = audiotsm.io.wav.WavReader(audio_file)
            writer = audiotsm.io.wav.WavWriter(output_file, 1, self.voice_config.sample_rate)
            
            wsola = audiotsm.wsola(1, speed=speed_ratio)
            wsola.run(reader, writer)
            
            return True
            
        except Exception as e:
            print(f"调整音频速度失败: {e}")
            return False
    
    def process_subtitle_file(self, subtitle_file: str, video_file: str, 
                            conversion_type: str = "英文转英文",
                            progress_callback=None) -> str:
        """处理字幕文件，生成完整的音频"""
        try:
            # 解析字幕文件
            segments = self._parse_subtitle_file(subtitle_file)
            if not segments:
                raise Exception("字幕文件解析失败")
            
            # 创建输出目录
            output_dir = os.path.dirname(subtitle_file)
            temp_dir = os.path.join(output_dir, "temp_audio")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 合成所有片段
            merged_audio = AudioSegment.empty()
            temp_files = []
            
            for i, (text, start_time, end_time) in enumerate(segments):
                if progress_callback:
                    progress = int((i / len(segments)) * 100)
                    progress_callback(progress, f"正在合成第 {i+1}/{len(segments)} 段...")
                
                # 翻译文本（如果需要）
                if "转" in conversion_type:
                    text = self._translate_text(text, conversion_type)
                
                # 添加静音（如果需要）
                if i == 0 and start_time > 0:
                    silence_duration = start_time * 1000
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence
                elif i > 0:
                    previous_end_time = segments[i - 1][2]
                    gap_duration = (start_time - previous_end_time) * 1000
                    if gap_duration > 0:
                        silence = AudioSegment.silent(duration=gap_duration)
                        merged_audio += silence
                
                # 合成音频片段
                segment_file = os.path.join(temp_dir, f"segment_{i}.wav")
                adjusted_file = os.path.join(temp_dir, f"adjusted_{i}.wav")
                
                if self.synthesize_text(text, segment_file):
                    # 调整音频时长
                    target_duration = end_time - start_time
                    if self.adjust_audio_speed(segment_file, target_duration, adjusted_file):
                        audio_segment = AudioSegment.from_file(adjusted_file)
                        merged_audio += audio_segment
                    
                    temp_files.extend([segment_file, adjusted_file])
            
            # 导出最终音频
            output_audio_file = os.path.join(output_dir, "synthesized_audio.wav")
            merged_audio.export(output_audio_file, format="wav")
            
            # 清理临时文件
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            os.rmdir(temp_dir)
            
            # 合成最终视频
            output_video = os.path.join(output_dir, "NewVideo.mp4")
            cmd = f'ffmpeg -y -i "{video_file}" -i "{output_audio_file}" -c:v copy -c:a aac "{output_video}"'
            subprocess.run(cmd, shell=True)
            
            return output_video
            
        except Exception as e:
            print(f"处理字幕文件失败: {e}")
            raise
    
    def _parse_subtitle_file(self, subtitle_file: str) -> List[Tuple[str, float, float]]:
        """解析SRT字幕文件"""
        segments = []
        
        with open(subtitle_file, 'r', encoding='gbk') as f:
            lines = f.readlines()
        
        for i in range(0, len(lines) - 1, 5):
            try:
                time_line = lines[i + 1].strip()
                text = lines[i + 2].strip()
                
                # 解析时间
                time_parts = time_line.split(" --> ")
                time_pattern = r'(\d{2}):(\d{2}):(\d{1,2}),(\d{1,3})'
                
                start_match = re.search(time_pattern, time_parts[0])
                end_match = re.search(time_pattern, time_parts[1])
                
                if start_match and end_match:
                    start_time = (int(start_match.group(1)) * 3600 + 
                                int(start_match.group(2)) * 60 + 
                                int(start_match.group(3)) + 
                                int(start_match.group(4)) / 1000)
                    
                    end_time = (int(end_match.group(1)) * 3600 + 
                              int(end_match.group(2)) * 60 + 
                              int(end_match.group(3)) + 
                              int(end_match.group(4)) / 1000)
                    
                    segments.append((text, start_time, end_time))
            except:
                continue
        
        return segments
    
    def _translate_text(self, text: str, conversion_type: str) -> str:
        """翻译文本"""
        if "中文转英文" in conversion_type:
            return self._translate_to_english(text)
        elif "英文转中文" in conversion_type:
            return self._translate_to_chinese(text)
        return text
    
    def _translate_to_english(self, text: str) -> str:
        """翻译为英文"""
        # 这里应该调用翻译API
        # 暂时返回原文
        return text
    
    def _translate_to_chinese(self, text: str) -> str:
        """翻译为中文"""
        # 这里应该调用翻译API
        # 暂时返回原文
        return text

# 全局实例
speech_synthesizer = EnhancedSpeechSynthesis()

# 便捷函数
def synthesize_text(text: str, output_file: str) -> bool:
    """合成文本为音频"""
    return speech_synthesizer.synthesize_text(text, output_file)

def process_video(video_file: str, subtitle_file: str, conversion_type: str = "英文转英文", 
                 progress_callback=None) -> str:
    """处理视频文件"""
    return speech_synthesizer.process_subtitle_file(
        subtitle_file, video_file, conversion_type, progress_callback
    )

if __name__ == "__main__":
    # 测试代码
    synthesizer = EnhancedSpeechSynthesis()
    
    # 测试文本合成
    test_text = "这是一个测试文本"
    output_file = "test_output.wav"
    
    success = synthesizer.synthesize_text(test_text, output_file)
    print(f"合成结果: {success}")
    
    if success and os.path.exists(output_file):
        print(f"音频文件已生成: {output_file}")
        os.remove(output_file)  # 清理测试文件 