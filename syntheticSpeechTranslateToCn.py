"""将subtitle.srt文件中的字幕内容依次交给edge_tts 进行合成，合成后临时创建mp3音频，
将该音频使用pydub转为合适的数据格式，存在segments列表中，同时记录下每段文本位于原音频中的开始时间 start_time 放入 start_times 列表中"""
import audiotsm
import numpy as np
import audiotsm.io.wav
import audiotsm.io.array
import random
import subprocess
import re
import pydub
import requests
import websocket
import datetime
import hashlib
from hashlib import md5
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os

from pydub import AudioSegment

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Text, voice_type="xiaoyan", speed=50, volume=50):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        # 修正参数：vcn=声音类型，speed=语速(0-100)，volume=音量(0-100)
        self.BusinessArgs = {
            "aue": "lame", 
            "auf": "audio/L16;rate=16000", 
            "vcn": voice_type,  # 使用传入的声音类型
            "speed": speed,     # 使用传入的语速
            "volume": volume,   # 使用传入的音量
            "tte": "utf8"
        }
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}
        #使用小语种须使用以下方式，此处的unicode指的是 utf16小端的编码方式，即"UTF-16LE"
        #self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-16')), "UTF8")}

    # 生成url
    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        # print("date: ",date)
        # print("v: ",v)
        # 此处打印出建立连接时候的url,参考本demo的时候可取消上方打印的注释，比对相同参数时生成的url与自己代码生成的url是否一致
        # print('websocket url :', url)
        return url

def on_message(ws, message):
    try:
        message =json.loads(message)
        code = message["code"]
        sid = message["sid"]
        audio = message["data"]["audio"]
        audio = base64.b64decode(audio)
        status = message["data"]["status"]
        print(message)
        if status == 2:
            print("ws is closed")
            ws.close()
        if code != 0:
            errMsg = message["message"]
            print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
        else:

            with open('./demo.mp3', 'ab') as f:
                f.write(audio)

    except Exception as e:
        print("receive msg,but parse exception:", e)



# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)


# 收到websocket关闭的处理
def on_close(ws):
    print("### closed ###")


# 收到websocket连接建立的处理
def on_open(ws):
    def run(*args):
        d = {"common": wsParam.CommonArgs,
             "business": wsParam.BusinessArgs,
             "data": wsParam.Data,
             }
        d = json.dumps(d)
        print("------>开始发送文本数据")
        ws.send(d)
        if os.path.exists('./demo.mp3'):
            os.remove('./demo.mp3')

    thread.start_new_thread(run, ())

# 保存语音文件
def save_audio_file(audio_data, filename):
    with open(filename, 'wb') as f:
        f.write(audio_data)

#根据原音频开始时间和结束时间对合成的音频进行加减速来使得时间段与原音频对应
def speed_change(audio_path, start_time, end_time, i):
    # 读取音频文件
    audio = AudioSegment.from_file(audio_path, format="wav")
    # audio = audio.set_channels(1)
    reader = audiotsm.io.wav.WavReader(audio_path)

    writer = audiotsm.io.wav.WavWriter("output_speed_to_cn" + str(i) + ".wav", 1, 16000)  # 1：单通道。  16000：采样率

    duration = audio.duration_seconds
    print(audio_path)
    print(duration)
    #计算加减速的倍率
    speed_rate = duration / (end_time - start_time)
    # speed_rate = 0.5
    print(speed_rate)
    # # 计算加速后的音频长度
    # new_length = int(len(audio) / speed_rate)

    # # 计算加速后的音频片段的开始和结束时间
    # start_frame = int(start_time * 1000)
    # end_frame = int(end_time * 1000)
    #
    # # 截取原音频片段
    # segment = audio[start_frame:end_frame]

    # 加速音频片段
    # accelerated_segment = segment._spawn(segment.raw_data, overrides={"frame_rate": int(segment.frame_rate * speed_rate)})
    # new_frame_rate = int(audio.frame_rate * speed_rate)
    # speed_up_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})

    wsola = audiotsm.wsola(1, speed=speed_rate)  # 1：单通道。  speed：速度
    wsola.run(reader, writer)

    # if speed_rate > 1:
    #     new_audio = audio.speedup(playback_speed=speed_rate)
    # elif speed_rate < 1:
    #     new_audio = audio.slowdown(playback_speed=speed_rate)
    # else:
    #     new_audio = audio

    # # 将加速后的音频片段写入文件
    # speed_up_audio.export("output_speed_to_en" + str(i) + ".wav", format="wav")
    return wsola

#将英文字幕文本翻译成中文
def translateToCn(text):
    # Set your own appid/appkey.
    appid = '20240510002047252'
    appkey = 'kTWYriLuEEEKr0BE70d1'

    # For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`
    from_lang = 'en'
    to_lang = 'zh'

    endpoint = 'http://api.fanyi.baidu.com'
    path = '/api/trans/vip/translate'
    url = endpoint + path

    query = text

    # Generate salt and sign
    def make_md5(s, encoding='utf-8'):
        return md5(s.encode(encoding)).hexdigest()

    salt = random.randint(32768, 65536)
    sign = make_md5(appid + query + str(salt) + appkey)

    # Build request
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

    # Send request
    r = requests.post(url, params=payload, headers=headers)
    result = r.json()
    print(result)
    # Show response
    return result['trans_result'][0]['dst']
    # print(json.dumps(result, indent=4, ensure_ascii=False))


"""没处理完"""
# 拼接配音片段
def merge_audio_segments(segments, start_times, total_duration, mp4name):
 # 创建一个空白的音频段作为初始片段
 merged_audio = AudioSegment.empty()
 # 检查是否需要在第一个片段之前添加静音
 if start_times[0] != 0:
     silence_duration = start_times[0]
     silence = AudioSegment.silent(duration=silence_duration)
     merged_audio += silence

 # 逐个连接音频片段
 for i in range(len(segments)):
     segment = segments[i]
     start_time = start_times[i]
     # 检查前一个片段的结束时间与当前片段的开始时间之间是否有间隔
     if i > 0:
         previous_end_time = start_times[i - 1] + len(segments[i - 1])
         silence_duration = start_time - previous_end_time
         # 可能存在字幕 语音对应问题
         if silence_duration > 0:
             silence = AudioSegment.silent(duration=silence_duration)
             merged_audio += silence

     # 连接当前片段
     merged_audio += segment
 # 检查总时长是否大于指定的时长，并丢弃多余的部分
 if len(merged_audio) > total_duration:
     merged_audio = merged_audio[:total_duration]
 merged_audio.export(f"./tmp/{mp4name}.wav", format="wav")
 return merged_audio


# def mergeSound(audiopath):
#     merged_audio = AudioSegment.empty()
#     datanames = os.listdir(audiopath)
#     # print(datanames)
#
#     for i in datanames:
#         # print(os.path.splitext(i)[1])
#         if os.path.splitext(i)[1]=='.mp4':
#             audio = video.audio
#             audio.write_audiofile(audiopath + '/' + os.path.splitext(i)[0] + '.wav')


def run(video_file, subtitle_file, output_path, voice_type="xiaoyan", speed=100, volume=80):
    """
    主处理函数 - 改进版字幕解析
    """
    print(f"开始处理: {video_file}")
    print(f"字幕文件: {subtitle_file}")
    print(f"输出路径: {output_path}")
    print(f"语音参数: 类型={voice_type}, 语速={speed}, 音量={volume}")
    
    # 创建一个空列表，用于存储每个段落的文本和开始时间
    segments = []

    # 读取字幕文件 - 支持多种编码
    subtitle_content = ""
    encoding_used = "utf-8"
    
    for encoding in ['utf-8', 'gbk', 'windows-1252', 'latin-1']:
        try:
            with open(subtitle_file, 'r', encoding=encoding) as f:
                subtitle_content = f.read()
            encoding_used = encoding
            print(f"✅ 成功使用 {encoding} 编码读取字幕文件")
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"使用 {encoding} 编码读取失败: {e}")
            continue
    
    if not subtitle_content:
        raise Exception("❌ 无法读取字幕文件，尝试了所有编码格式")
    
    print(f"字幕文件内容长度: {len(subtitle_content)} 字符")
    
    # 清理和验证字幕内容
    lines = subtitle_content.strip().split('\n')
    print(f"字幕文件总行数: {len(lines)}")
    
    # 显示前几行用于调试
    print("字幕文件前10行:")
    for i, line in enumerate(lines[:10]):
        print(f"  {i+1:2d}: {repr(line)}")
    
    # 改进的字幕解析逻辑
    i = 0
    while i < len(lines):
        # 跳过空行
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        if i >= len(lines):
            break
            
        # 检查是否是序号行
        if i < len(lines) and lines[i].strip().isdigit():
            sequence_num = lines[i].strip()
            i += 1
            
            # 读取时间行
            if i < len(lines) and "-->" in lines[i]:
                soundTime = lines[i].strip()
                i += 1
                
                # 读取文本行（可能有多行）
                text_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                    line_text = lines[i].strip()
                    # 过滤掉明显错误的逗号分隔字符
                    if not isCommaSeperatedChars(line_text):
                        text_lines.append(line_text)
                    else:
                        print(f"⚠️ 跳过疑似错误的逗号分隔文本: {line_text[:50]}...")
                    i += 1
                
                if text_lines:
                    # 合并多行文本
                    text = ' '.join(text_lines).strip()
                    
                    # 进一步清理文本
                    text = cleanSubtitleText(text)
                    
                    if text and len(text) > 1:  # 确保文本有意义
                        # 解析时间
                        time_parts = soundTime.split(" --> ")
                        if len(time_parts) == 2:
                            # 定义时间正则表达式模式
                            time_pattern = r'(\d{2}):(\d{2}):(\d{1,2}),(\d{1,3})'

                            start_time_match = re.search(time_pattern, time_parts[0])
                            end_time_match = re.search(time_pattern, time_parts[1])
                            
                            if start_time_match and end_time_match:
                                # 计算开始时间戳
                                start_time_hours = int(start_time_match.group(1))
                                start_time_minutes = int(start_time_match.group(2))
                                start_time_seconds = int(start_time_match.group(3))
                                start_time_milliseconds = int(start_time_match.group(4))

                                # 计算结束时间戳
                                end_time_hours = int(end_time_match.group(1))
                                end_time_minutes = int(end_time_match.group(2))
                                end_time_seconds = int(end_time_match.group(3))
                                end_time_milliseconds = int(end_time_match.group(4))

                                # 转换为秒
                                start_time_timestamp = start_time_hours * 3600 + start_time_minutes * 60 + start_time_seconds + start_time_milliseconds / 1000
                                end_time_timestamp = end_time_hours * 3600 + end_time_minutes * 60 + end_time_seconds + end_time_milliseconds / 1000

                                # 添加到segments列表中
                                segments.append((text, start_time_timestamp, end_time_timestamp))
                                print(f"✅ 解析字幕 {sequence_num}: {text[:50]}...")
            else:
                i += 1
        else:
            i += 1

    print(f"✅ 成功解析 {len(segments)} 条字幕")

    if not segments:
        print("❌ 警告：没有解析到任何字幕内容")
        return

    # 显示解析结果示例
    print("\n前3条解析结果:")
    for i, (text, start, end) in enumerate(segments[:3]):
        print(f"  {i+1}. [{start:.1f}s-{end:.1f}s] {text}")

    # 合成语音
    merged_audio = AudioSegment.empty()
    tmpname = 'to_cn_audio_segment_'
    changeSpeedTmpname = 'output_speed_to_cn'
    
    for i, (text, start_time, end_time) in enumerate(segments):
        try:
            # 添加静音间隔
            if i == 0 and start_time != 0:
                silence_duration = start_time * 1000
                print(f"添加开始静音: {silence_duration}ms")
                silence = AudioSegment.silent(duration=silence_duration)
                merged_audio += silence
            elif i > 0:
                previous_end_time = segments[i - 1][2]
                silence_duration = (start_time - previous_end_time) * 1000
                if silence_duration > 0:
                    print(f"添加间隔静音: {silence_duration}ms")
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence

            print(f"处理字幕 {i+1}/{len(segments)}: {text}")
            
            # 翻译文本
            try:
                translated_text = translateToCn(text)
                print(f"翻译结果: {translated_text}")
            except Exception as e:
                print(f"翻译失败，使用原文: {e}")
                translated_text = text

            # 语音合成
            global wsParam
            wsParam = Ws_Param(
                APPID='dece0a1f', 
                APISecret='Y2I4YTUxMDljZjk2YzAwZGMzNTgwYTNl',
                           APIKey='5cc4877fa4b7d173d8f1c085e50a4788',
                Text=translated_text,
                voice_type=voice_type,
                speed=speed,
                volume=volume
            )
            
            websocket.enableTrace(False)
            wsUrl = wsParam.create_url()
            ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            
            # 转换音频格式
            command = f'ffmpeg -y -i demo.mp3 {tmpname}{i}.wav'
            result = os.system(command)
            if result != 0:
                print(f"音频转换失败: {command}")
                continue
            
            # 调整语音速度
            speed_change(f'{tmpname}{i}.wav', start_time, end_time, i)
            
            # 加载调速后的音频
            if os.path.exists(f'{changeSpeedTmpname}{i}.wav'):
                audio_data = AudioSegment.from_file(f'{changeSpeedTmpname}{i}.wav', format="wav")
                merged_audio += audio_data
                print(f"语音片段 {i+1} 合成完成")
            else:
                print(f"警告: 调速文件不存在 {changeSpeedTmpname}{i}.wav")
            
        except Exception as e:
            print(f"处理字幕片段 {i} 时出错: {e}")
            continue

    # 导出合成的音频
    output_audio_path = "./newOutputToCn.wav"
    merged_audio.export(output_audio_path, format="wav")
    print(f"合成音频已保存: {output_audio_path}")

    # 确定最终输出路径
    if output_path and output_path.endswith('.mp4'):
        final_output_path = output_path
    else:
        # 根据输入视频文件名和转换类型生成输出文件名
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        output_dir = os.path.dirname(subtitle_file)
        final_output_path = os.path.join(output_dir, f"{base_name}_en_to_cn.mp4").replace("\\", "/")

    print(f"最终输出路径: {final_output_path}")

    # 合并视频和音频
    try:
        # 检查音频文件是否存在且有内容
        if not os.path.exists(output_audio_path):
            print(f"❌ 错误: 音频文件不存在 {output_audio_path}")
            return None
            
        audio_size = os.path.getsize(output_audio_path)
        if audio_size == 0:
            print(f"❌ 错误: 音频文件为空 {output_audio_path}")
            return None
            
        print(f"✅ 音频文件验证通过: {output_audio_path} ({audio_size} bytes)")
        
        # 检查视频文件
        if not os.path.exists(video_file):
            print(f"❌ 错误: 视频文件不存在 {video_file}")
            return None
            
        print(f"✅ 视频文件验证通过: {video_file}")
        
        # 使用改进的FFmpeg命令合并视频和音频
        cmd = [
            'ffmpeg', '-y',
            '-i', video_file,      # 输入视频（无声）
            '-i', output_audio_path,  # 输入音频
            '-c:v', 'copy',        # 复制视频流，不重新编码
            '-c:a', 'aac',         # 音频编码为AAC
            '-b:a', '128k',        # 音频比特率
            '-shortest',           # 以最短的流为准
            final_output_path
        ]
        
        print(f"执行合并命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        
        if result.returncode == 0:
            # 验证输出文件
            if os.path.exists(final_output_path):
                output_size = os.path.getsize(final_output_path)
                print(f"✅ 视频合并成功: {final_output_path} ({output_size} bytes)")
                
                # 验证输出视频是否有音频轨道
                verify_cmd = [
                    'ffprobe', '-v', 'quiet', '-show_streams', 
                    '-select_streams', 'a', final_output_path
                ]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                if verify_result.returncode == 0 and verify_result.stdout.strip():
                    print("✅ 输出视频包含音频轨道")
                else:
                    print("⚠️ 警告: 输出视频可能没有音频轨道")
            else:
                print(f"❌ 错误: 输出文件未生成 {final_output_path}")
                return None
        else:
            print(f"❌ 视频合并失败 (返回码: {result.returncode})")
            print(f"错误输出: {result.stderr}")
            
            # 尝试备用合并方法
            print("尝试备用合并方法...")
            backup_cmd = [
                'ffmpeg', '-y',
                '-i', video_file,
                '-i', output_audio_path,
                '-map', '0:v',         # 映射视频流
                '-map', '1:a',         # 映射音频流
                '-c:v', 'copy',
                '-c:a', 'aac',
                final_output_path
            ]
            
            print(f"执行备用命令: {' '.join(backup_cmd)}")
            backup_result = subprocess.run(backup_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
            
            if backup_result.returncode == 0:
                print(f"✅ 备用方法合并成功: {final_output_path}")
            else:
                print(f"❌ 备用方法也失败: {backup_result.stderr}")
                return None
            
    except subprocess.TimeoutExpired:
        print("❌ 视频合并超时")
        return None
    except Exception as e:
        print(f"❌ 视频合并异常: {e}")
        return None

    # 清理临时文件
    try:
        for i in range(len(segments)):
            temp_files = [
                f'{tmpname}{i}.wav',
                f'{changeSpeedTmpname}{i}.wav'
            ]
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        # 清理demo.mp3
        if os.path.exists('demo.mp3'):
            os.remove('demo.mp3')
        if os.path.exists(output_audio_path):
            os.remove(output_audio_path)
            
        print("临时文件清理完成")
    except Exception as e:
        print(f"清理临时文件时出错: {e}")

    return final_output_path

def isCommaSeperatedChars(text):
    """检测是否是逗号分隔的字符（错误格式）"""
    if not text:
        return False
    
    # 检查是否大部分字符都被逗号分隔
    comma_count = text.count(',')
    char_count = len(text.replace(',', '').replace(' ', ''))
    
    # 如果逗号数量接近字符数量，可能是错误格式
    if char_count > 0 and comma_count / char_count > 0.5:
        return True
    
    # 检查是否是单字符逗号分隔模式，如 "H,e,l,l,o"
    parts = text.split(',')
    if len(parts) > 3:
        single_char_count = sum(1 for part in parts if len(part.strip()) == 1)
        if single_char_count / len(parts) > 0.7:  # 70%以上是单字符
            return True
    
    return False

def cleanSubtitleText(text):
    """清理字幕文本"""
    if not text:
        return ""
    
    # 移除多余的空格
    text = ' '.join(text.split())
    
    # 如果检测到逗号分隔的字符，尝试修复
    if isCommaSeperatedChars(text):
        # 尝试移除逗号并重新组合
        cleaned = text.replace(',', '').replace(' ', '')
        if len(cleaned) > 0:
            print(f"修复逗号分隔文本: {text[:30]}... -> {cleaned[:30]}...")
            return cleaned
    
    # 移除控制字符但保留正常标点
    cleaned_chars = []
    for char in text:
        if char.isprintable() or char.isspace():
            cleaned_chars.append(char)
    
    result = ''.join(cleaned_chars).strip()
    
    # 确保文本不为空且有意义
    if len(result) < 2:
        return ""
    
    return result

