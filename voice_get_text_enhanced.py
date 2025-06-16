import os
import wave
import moviepy.editor as mp
import time

def get_text_from_video(video_path):
    """
    从视频文件中提取音频并进行语音识别
    返回识别出的文本内容
    """
    try:
        # 临时音频文件路径
        temp_audio = "temp_audio_for_detection.wav"
        
        # 从视频中提取音频
        video = mp.VideoFileClip(video_path)
        audio = video.audio
        
        # 保存为wav文件（限制长度以提高速度）
        duration = min(audio.duration, 30)  # 只取前30秒进行检测
        audio_clip = audio.subclip(0, duration)
        audio_clip.write_audiofile(temp_audio, verbose=False, logger=None)
        
        # 清理资源
        audio_clip.close()
        audio.close()
        video.close()
        
        # 进行语音识别
        import video_to_txt
        result_text = ""
        
        # 创建临时保存目录
        temp_dir = "temp_detection"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        try:
            # 使用现有的语音识别功能
            video_to_txt.run(temp_audio, temp_dir)
            
            # 读取识别结果
            subtitle_file = os.path.join(temp_dir, "subtitle.srt")
            if os.path.exists(subtitle_file):
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    result_text = f.read()
        except Exception as e:
            print(f"语音识别失败: {e}")
        
        # 清理临时文件
        try:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"清理临时文件失败: {e}")
        
        return result_text
        
    except Exception as e:
        print(f"提取音频失败: {e}")
        return ""

def extract_text_content(srt_content):
    """从SRT字幕内容中提取纯文本"""
    if not srt_content:
        return ""
    
    import re
    # 去除时间戳和序号
    clean_text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_content)
    clean_text = re.sub(r'^\d+\n', '', clean_text, flags=re.MULTILINE)
    clean_text = clean_text.strip()
    
    return clean_text

if __name__ == "__main__":
    # 测试代码
    test_video = "test.mp4"
    if os.path.exists(test_video):
        text = get_text_from_video(test_video)
        print("识别出的文本:", text)
        clean_text = extract_text_content(text)
        print("纯文本内容:", clean_text) 