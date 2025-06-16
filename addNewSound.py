import os
import subprocess

def del_audio(video_file, save_file, output_filename=None):
    """删除视频中的音频，生成无声视频"""
    try:
        # 标准化路径
        video_file = video_file.replace("\\", '/')
        save_file = save_file.replace("\\", '/')
        
        # 确保输出目录存在
        os.makedirs(save_file, exist_ok=True)
        
        # 检查输入文件是否存在
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"视频文件不存在: {video_file}")
        
        print(f"正在生成无声视频: {video_file}")
        
        # 生成输出文件路径 - 支持自定义文件名
        if output_filename:
            output_path = os.path.join(save_file, output_filename).replace("\\", '/')
        else:
            # 默认文件名，使用视频文件名作为前缀避免冲突
            video_name = os.path.splitext(os.path.basename(video_file))[0]
            import re
            clean_name = re.sub(r'[^\w\-_]', '_', video_name)
            output_path = os.path.join(save_file, f'{clean_name}_videoWithoutAudio.mp4').replace("\\", '/')
        
        # 使用ffmpeg删除音频
        cmd = [
            'ffmpeg', '-y',  # -y 覆盖输出文件
            '-i', video_file,  # 输入视频文件
            '-an',  # 删除音频
            '-c:v', 'copy',  # 复制视频流，不重新编码
            output_path  # 输出文件
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"无声视频生成成功: {output_path}")
            
            # 验证文件是否真的生成了
            if os.path.exists(output_path):
                return output_path
            else:
                raise FileNotFoundError(f"无声视频文件生成失败: {output_path}")
        else:
            print(f"ffmpeg错误: {result.stderr}")
            raise RuntimeError(f"ffmpeg执行失败: {result.stderr}")
            
    except Exception as e:
        print(f"生成无声视频失败: {e}")
        raise

def replace_audio(video_without_sound, audio_file, output_path):
    """替换视频音频"""
    try:
        # 标准化路径
        video_without_sound = video_without_sound.replace("\\", '/')
        audio_file = audio_file.replace("\\", '/')
        output_path = output_path.replace("\\", '/')
        
        # 检查输入文件是否存在
        if not os.path.exists(video_without_sound):
            raise FileNotFoundError(f"无声视频文件不存在: {video_without_sound}")
        
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")
        
        print(f"正在替换音频: {video_without_sound} + {audio_file} -> {output_path}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用ffmpeg替换音频
        cmd = [
            'ffmpeg', '-y',  # -y 覆盖输出文件
            '-i', video_without_sound,  # 输入视频文件
            '-i', audio_file,  # 输入音频文件
            '-c:v', 'copy',  # 复制视频流
            '-c:a', 'aac',  # 音频编码为AAC
            '-map', '0:v:0',  # 映射第一个输入的视频流
            '-map', '1:a:0',  # 映射第二个输入的音频流
            output_path  # 输出文件
        ]
        
        print(f"执行命令: {' '.join(cmd)}")
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f'音频替换完成: {output_path}')
            
            # 验证文件是否真的生成了
            if os.path.exists(output_path):
                return output_path
            else:
                raise FileNotFoundError(f"最终视频文件生成失败: {output_path}")
        else:
            print(f"ffmpeg错误: {result.stderr}")
            raise RuntimeError(f"ffmpeg执行失败: {result.stderr}")
            
    except Exception as e:
        print(f'音频替换失败: {e}')
        raise

# 测试代码（如果直接运行此文件）
if __name__ == "__main__":
    # 测试用例
    test_video = "test_video.mp4"
    test_output_dir = "./output"
    
    if os.path.exists(test_video):
        try:
            result = del_audio(test_video, test_output_dir)
            print(f"测试成功: {result}")
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print("测试视频文件不存在，跳过测试")

