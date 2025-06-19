import os
import subprocess

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import AudioFileClip

def videoToWav(videoPath, savePath, output_filename=None):
    """从视频中提取音频并保存为WAV格式"""
    try:
        # 标准化路径
        videoPath = videoPath.replace('\\', '/')
        savePath = savePath.replace('\\', '/')
        
        # 确保输出目录存在
        os.makedirs(savePath, exist_ok=True)
        
        # 生成输出文件名 - 支持自定义文件名
        if output_filename:
            output_path = os.path.join(savePath, output_filename).replace('\\', '/')
        else:
            # 默认文件名，使用视频文件名作为前缀避免冲突
            video_name = os.path.splitext(os.path.basename(videoPath))[0]
            import re
            clean_name = re.sub(r'[^\w\-_]', '_', video_name)
            output_path = os.path.join(savePath, f'{clean_name}_extractedAudio.wav').replace('\\', '/')
        
        # 使用VideoFileClip提取音频（更稳定）
        with VideoFileClip(videoPath) as video:
            if video.audio is None:
                raise Exception("视频文件没有音频轨道")
            
            audio = video.audio
            
            # 检查音频对象是否有效
            if audio is None:
                raise Exception("无法从视频中提取音频对象")
            
            try:
                # 写入音频文件，移除不支持的temp_audiofile参数
                audio.write_audiofile(
                    output_path, 
                    verbose=False, 
                    logger=None
                )
                
            except Exception as write_error:
                print(f"MoviePy写入失败: {write_error}")
                
                # 备用方案：使用ffmpeg直接提取，添加编码处理
                cmd = ['ffmpeg', '-y', '-i', videoPath, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', output_path]
                
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                    if result.returncode != 0:
                        raise Exception(f"ffmpeg提取音频失败: {result.stderr}")
                except UnicodeDecodeError:
                    # 如果编码失败，尝试不解码输出
                    result = subprocess.run(cmd, capture_output=True, text=False)
                    if result.returncode != 0:
                        raise Exception(f"ffmpeg提取音频失败")
        
        # 验证输出文件
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception(f"音频文件生成失败或为空: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"音频提取失败: {e}")
        raise

def changeCoding(wavPath, outputPath=None):
    """改变音频编码格式为16kHz单声道"""
    try:
        # 标准化路径
        wavPath = wavPath.replace('\\', '/')
        
        if not os.path.exists(wavPath):
            raise FileNotFoundError(f"音频文件不存在: {wavPath}")
        
        # 如果没有指定输出路径，创建临时文件名避免冲突
        if outputPath is None:
            base_dir = os.path.dirname(wavPath)
            base_name = os.path.splitext(os.path.basename(wavPath))[0]
            temp_output = os.path.join(base_dir, f"{base_name}_temp.wav").replace('\\', '/')
        else:
            temp_output = outputPath.replace('\\', '/')
        
        # 使用ffmpeg转换音频格式
        cmd = [
            "ffmpeg", "-y",  # -y 覆盖输出文件
            "-i", wavPath,   # 输入文件
            "-ar", "16000",  # 采样率16kHz
            "-ac", "1",      # 单声道
            "-acodec", "pcm_s16le",  # 编码格式
            temp_output      # 输出到临时文件
        ]
        
        # 执行命令，改善编码处理
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        except UnicodeDecodeError:
            # 如果编码问题，尝试不解码输出
            result = subprocess.run(cmd, capture_output=True, text=False)
            # 转换返回码检查，避免访问.stderr
            if result.returncode != 0:
                print("ffmpeg转换失败（编码问题），使用原始音频文件")
                return wavPath
            else:
                # 继续后续处理...
                if outputPath is None:
                    try:
                        os.remove(wavPath)
                        os.rename(temp_output, wavPath)
                        return wavPath
                    except Exception as e:
                        print(f"文件替换失败: {e}")
                        return temp_output
                else:
                    return temp_output
        
        if result.returncode == 0:
            # 如果是覆盖原文件，则替换原文件
            if outputPath is None:
                try:
                    # 删除原文件
                    os.remove(wavPath)
                    # 重命名临时文件为原文件名
                    os.rename(temp_output, wavPath)
                    return wavPath
                except Exception as e:
                    print(f"文件替换失败: {e}")
                    # 如果替换失败，返回临时文件路径
                    return temp_output
            else:
                return temp_output
        else:
            print(f"ffmpeg错误: {result.stderr}")
            # 如果ffmpeg失败，返回原文件
            return wavPath
            
    except FileNotFoundError as e:
        print(f"文件不存在: {e}")
        raise
    except Exception as e:
        print(f"音频编码转换失败: {e}")
        # 如果转换失败，返回原文件
    return wavPath

def run(video_path, save_path, output_filename=None):
    """
    主函数：从视频中提取音频并转换格式
    
    Args:
        video_path: 视频文件路径
        save_path: 保存目录路径
        output_filename: 可选的输出文件名，如果不提供则自动生成
    
    Returns:
        str: 最终音频文件路径
    """
    try:
        # 步骤1: 提取音频
        wav_path = videoToWav(video_path, save_path, output_filename)
        
        # 步骤2: 转换音频格式
        final_path = changeCoding(wav_path)
        
        return final_path
        
    except Exception as e:
        print(f"音频处理失败: {e}")
        raise

# 测试代码（如果直接运行此文件）
if __name__ == "__main__":
    # 测试用例
    test_video = "test_video.mp4"
    test_output = "./output"
    
    if os.path.exists(test_video):
        try:
            result = run(test_video, test_output)
            print(f"测试成功: {result}")
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print("测试视频文件不存在，跳过测试")
