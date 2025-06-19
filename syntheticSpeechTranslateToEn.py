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
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"aue": "lame", "auf": "audio/L16;rate=16000", "vcn": "x4_EnUs_Laura_education", "tte": "utf8"}
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

    writer = audiotsm.io.wav.WavWriter("output_speed_to_en" + str(i) + ".wav", 1, 16000)  # 1：单通道。  16000：采样率

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

#将中文字幕文本翻译成英文
def translateToEn(text):
    # Set your own appid/appkey.
    appid = '20240510002047252'
    appkey = 'kTWYriLuEEEKr0BE70d1'

    # For list of language codes, please refer to `https://api.fanyi.baidu.com/doc/21`
    from_lang = 'zh'
    to_lang = 'en'

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

    # Show response
    return result['trans_result'][0]['dst']
    # print(json.dumps(result, indent=4, ensure_ascii=False))





# def mergeSound(audiopath):
#     merged_audio = AudioSegment.empty()
#     datanames = os.listdir(audiopath)
#     # print(datanames)
#
#     for i in datanames:
#         # print(os.path.splitext(i)[1])
#         if os.path.splitext(i)[1]=='.mp4':
#             audio = video.audio
#             audio.write_audiofile(audiopath + '/' + os.path.splitext(i)[0] + '.mp3')


def run(video_file, subtitle_file, output_path, voice_type="x4_EnUs_Laura_education", speed=100, volume=80):
    # 创建一个空列表，用于存储每个段落的文本和开始时间
    segments = []

    # 读取字幕文件 - 支持多种编码
    subtitle_content = ""
    for encoding in ['utf-8', 'gbk', 'windows-1252']:
        try:
            with open(subtitle_file, 'r', encoding=encoding) as f:
                subtitle_content = f.read()
            print(f"成功使用 {encoding} 编码读取字幕文件")
            break
        except UnicodeDecodeError:
            continue
    
    if not subtitle_content:
        raise Exception("无法读取字幕文件，尝试了多种编码格式")
    
    lines = subtitle_content.strip().split('\n')

    # 解析字幕文件
    for i in range(0, len(lines)-1, 4):  # 修正步长，SRT格式通常是4行一组
        if i + 2 >= len(lines):
            break
            
        try:
            soundTime = lines[i + 1].strip()
            text = lines[i + 2].strip()
            
            if not soundTime or not text or '-->' not in soundTime:
                continue
                
            print(f"处理字幕 {i//4 + 1}: {text}")

            # 以 "-->" 作为分界线，将数据分割成起始时间和结束时间
            time_parts = soundTime.split(" --> ")

            # 定义起始时间和结束时间的正则表达式模式
            time_pattern = r'(\d{2}):(\d{2}):(\d{1,2}),(\d{1,3})'

            # 分别匹配起始时间和结束时间
            start_time_match = re.search(time_pattern, time_parts[0])
            end_time_match = re.search(time_pattern, time_parts[1])
            
            if start_time_match and end_time_match:
                start_time_hours = int(start_time_match.group(1))
                start_time_minutes = int(start_time_match.group(2))
                start_time_seconds = int(start_time_match.group(3))
                start_time_milliseconds = int(start_time_match.group(4))

                end_time_hours = int(end_time_match.group(1))
                end_time_minutes = int(end_time_match.group(2))
                end_time_seconds = int(end_time_match.group(3))
                end_time_milliseconds = int(end_time_match.group(4))

                # 计算开始时间和结束时间的时间戳
                start_time_timestamp = start_time_hours * 3600 + start_time_minutes * 60 + start_time_seconds + start_time_milliseconds / 1000
                end_time_timestamp = end_time_hours * 3600 + end_time_minutes * 60 + end_time_seconds + end_time_milliseconds / 1000

                # 添加到segments列表中
                segments.append((text, start_time_timestamp, end_time_timestamp))
                
        except Exception as e:
            print(f"解析字幕行 {i} 时出错: {e}")
            continue

    print(f"成功解析 {len(segments)} 个字幕片段")

    index = 0
    merged_audio = AudioSegment.empty()
    tmpname = 'to_en_audio_segment_'
    changeSpeedTmpname = 'output_speed_to_en'
    
    for i, (text, start_time, end_time) in enumerate(segments):
        if i == 0 and start_time != 0:
            silence_duration = start_time * 1000
            print("silence_duration:", silence_duration)
            silence = AudioSegment.silent(duration=silence_duration)
            merged_audio += silence

        else:
            # 检查当前片段与前一个片段之间的间隔
            if i > 0:
                previous_end_time = segments[i - 1][2]
                print("Index:", i)
                print("previous_end_time:", previous_end_time)
                silence_duration = (start_time - previous_end_time) * 1000
                print("silence_duration:", silence_duration)
                if silence_duration > 0:
                    silence = AudioSegment.silent(duration=silence_duration)
                    merged_audio += silence
        print(text)
        text = translateToEn(text)
        print("translate:", text)
        global wsParam
        wsParam = Ws_Param(APPID='dece0a1f', APISecret='Y2I4YTUxMDljZjk2YzAwZGMzNTgwYTNl',
                           APIKey='5cc4877fa4b7d173d8f1c085e50a4788',
                           Text=text)
        websocket.enableTrace(False)
        wsUrl = wsParam.create_url()
        ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
        ws.on_open = on_open
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        command = 'ffmpeg ' + '-y -i ' + 'demo.mp3 to_en_audio_segment_' + str(i) + '.wav'
        os.system(command)
        # 合并所有语音片段
        speed_change(tmpname + str(i) + '.wav', start_time, end_time, i)
        print("语音速度已经更改")
        audio_data = AudioSegment.from_file(changeSpeedTmpname + str(i) + '.wav', format="wav")
        print(f"语音片段已经合成 {i} ")
        # time.sleep(end_time - start_time)
        merged_audio += audio_data
        print(f"Segment {i} completed")
    
    merged_audio.export(f"./newOutputToEn.wav", format="wav")

    # 确定最终输出路径
    if output_path and output_path.endswith('.mp4'):
        final_output_path = output_path.replace("\\", "/")
    else:
        # 如果没有指定输出路径，使用默认命名
        output_dir = os.path.dirname(subtitle_file)
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        final_output_path = os.path.join(output_dir, f"{base_name}_cn_to_en.mp4").replace("\\", "/")

    print(f"开始合并视频和音频，输出到: {final_output_path}")

    # 删除所有语音片段
    for i in range(len(segments)):
        try:
            os.remove(f'to_en_audio_segment_{i}.wav')
            os.remove(f'output_speed_to_en{i}.wav')
        except FileNotFoundError:
            pass

    # 合并视频和音频
    try:
        subprocess.run(['ffmpeg', '-y', '-i', video_file, '-i', 'newOutputToEn.wav', '-c', 'copy', final_output_path],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
        print(f"视频合成成功: {final_output_path}")
        
        # 清理临时音频文件
        try:
            os.remove('newOutputToEn.wav')
            if os.path.exists('demo.mp3'):
                os.remove('demo.mp3')
        except FileNotFoundError:
            pass
            
        return final_output_path
        
    except subprocess.CalledProcessError as e:
        print(f"视频合成失败: {e}")
        raise Exception(f"视频合成失败: {e}")
    except Exception as e:
        print(f"合成过程中出现错误: {e}")
        raise

