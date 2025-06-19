# -*- coding: utf-8 -*-
import json
import os
import voice_get_text
import datetime

def load_api_config():
    """从config.json加载API配置"""
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            appid = config.get('xunfei_appid', 'c9f38a98')
            secret_key = config.get('xunfei_apisecret', 'a8b81c43d2528e7edcd6a826ec31ee19')
            
            return appid, secret_key
        else:
            return 'c9f38a98', 'a8b81c43d2528e7edcd6a826ec31ee19'
            
    except Exception as e:
        print(f"❌ 加载API配置失败: {e}，使用默认配置")
        return 'c9f38a98', 'a8b81c43d2528e7edcd6a826ec31ee19'

def get_format_time(time_long):
    """格式化时间戳"""
    def format_number(num):
        if len(str(num)) > 1:
            return str(num)
        else:
            return "0" + str(num)
    
    myhour = 0
    mysecond = int(time_long / 1000)
    myminute = 0
    mymilsec = 0
    
    if mysecond < 1:
        return "00:00:00,%s" % (time_long)
    else:
        if mysecond > 60:
            myminute = int(mysecond / 60)
            if myminute > 60:
                myhour = int(myminute / 60)
                myminute = myminute - myhour * 60
                mysecond = mysecond - myhour * 3600 - myminute * 60
                mymilsec = time_long - 1000 * (mysecond + myhour * 3600 + myminute * 60)
                return "%s:%s:%s,%s" % (format_number(myhour), format_number(myminute), 
                                      format_number(mysecond), format_number(mymilsec))
            else:
                mysecond = int(mysecond - myminute * 60)
                mymilsec = time_long - 1000 * (mysecond + myminute * 60)
                return "00:%s:%s,%s" % (format_number(myminute), format_number(mysecond), 
                                      format_number(mymilsec))
        else:
            mymilsec = time_long - mysecond * 1000
            return "00:00:%s,%s" % (mysecond, mymilsec)

def run(video_path, save_path='./', output_filename=None):
    """
    语音识别主函数 - 优化版
    支持多种音频/视频格式，生成高质量SRT字幕文件
    
    Args:
        video_path: 音频/视频文件路径
        save_path: 输出目录路径
        output_filename: 自定义输出文件名（可选）
    
    Returns:
        生成的字幕文件路径
    """
    try:
        # 从config.json加载API配置
        appid, secret_key = load_api_config()
        
        # 创建API请求对象
        api = voice_get_text.RequestApi(
            appid=appid,
            secret_key=secret_key,
            upload_file_path=video_path
        )
        
        print(f"🎙️ 开始语音识别: {video_path}")
        myresult = api.all_api_request()
        
        # 解析API返回的数据
        data_list = json.loads(myresult['data'])
        
        # 清理数据，移除问题字符
        for item in data_list:
            if 'onebest' in item:
                # 清理文本，移除不必要的字符，但保持原始内容
                text = item['onebest']
                # 移除可能的控制字符，但保持正常的标点符号
                text = ''.join(char for char in text if char.isprintable() or char.isspace())
                item['onebest'] = text.strip()
        
        # 清理字符串数据
        for d in data_list:
            for key, value in d.items():
                if isinstance(value, str):
                    d[key] = value.strip()

        # 合并短句子为完整句子，提高翻译质量
        merged_segments = merge_short_segments(data_list)
        
        # 生成SRT格式字幕
        myword = ""
        flag_num = 0
        
        for item in merged_segments:
            flag_num += 1
            try:
                bg = get_format_time(int(item["bg"]))
                ed = get_format_time(int(item["ed"]))
                real_word = item["onebest"]
                
                # 格式化SRT条目
                newword = f"{flag_num}\n{bg} --> {ed}\n{real_word}\n\n"
                myword += newword
                
            except (KeyError, ValueError) as e:
                print(f"处理字幕条目 {flag_num} 时出错: {e}")
                continue
        
        # 确保输出目录存在
        os.makedirs(save_path, exist_ok=True)
        
        # 生成文件路径 - 支持自定义文件名
        if output_filename:
            filename = output_filename
        else:
            # 默认文件名，使用音频文件名作为前缀避免冲突
            audio_name = os.path.splitext(os.path.basename(video_path))[0]
            import re
            clean_name = re.sub(r'[^\w\-_]', '_', audio_name)
            filename = f'{clean_name}_subtitle.srt'
            
        path_file = os.path.join(save_path, filename).replace("\\", "/")
        
        # 使用UTF-8编码写入文件
        with open(path_file, 'w', encoding='utf-8') as f:
            f.write(myword)
        
        print(f'语音识别完成，字幕文件已保存: {path_file}')
        return path_file
        
    except Exception as e:
        print(f"语音识别失败: {e}")
        raise

def merge_short_segments(data_list):
    """合并短句子为完整句子，提高翻译质量"""
    if not data_list:
        return data_list
    
    merged_segments = []
    current_segment = None
    
    for item in data_list:
        if 'onebest' not in item or 'bg' not in item or 'ed' not in item:
            continue
            
        text = item['onebest'].strip()
        
        # 跳过空文本或过短的文本
        if not text or len(text) < 2:
            continue
        
        # 如果当前没有段落，开始新段落
        if current_segment is None:
            current_segment = {
                'bg': item['bg'],
                'ed': item['ed'],
                'onebest': text
            }
        else:
            # 检查是否应该合并
            time_gap = int(item['bg']) - int(current_segment['ed'])
            current_text = current_segment['onebest']
            
            # 合并条件：
            # 1. 时间间隔小于2秒
            # 2. 当前段落长度小于50字符
            # 3. 新文本不是以句号、问号、感叹号结尾
            should_merge = (
                time_gap < 2000 and  # 2秒内
                len(current_text) < 50 and  # 当前段落不太长
                not current_text.endswith(('.', '。', '!', '！', '?', '？'))
            )
            
            if should_merge:
                # 合并到当前段落
                current_segment['ed'] = item['ed']
                # 智能添加空格或连接
                if current_text and text:
                    # 如果是中文，直接连接；如果是英文，添加空格
                    if any('\u4e00' <= char <= '\u9fff' for char in current_text + text):
                        current_segment['onebest'] = current_text + text
                    else:
                        current_segment['onebest'] = current_text + ' ' + text
            else:
                # 完成当前段落，开始新段落
                merged_segments.append(current_segment)
                current_segment = {
                    'bg': item['bg'],
                    'ed': item['ed'],
                    'onebest': text
                }
    
    # 添加最后一个段落
    if current_segment is not None:
        merged_segments.append(current_segment)
    
    return merged_segments

# 测试代码
if __name__ == "__main__":
    # 测试用例
    test_audio = "test_audio.wav"
    
    if os.path.exists(test_audio):
        try:
            result = run(test_audio, "./")
            print(f"测试成功: {result}")
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print("测试音频文件不存在，跳过测试")
