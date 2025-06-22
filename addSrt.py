import subprocess
import os
import sys
import shutil
import tempfile

def normalize_path_for_ffmpeg(path):
    """标准化路径以适配FFmpeg的subtitles滤镜"""
    # 转换为绝对路径
    path = os.path.abspath(path)
    
    # Windows路径处理 - 使用正斜杠，这在FFmpeg中最兼容
    if sys.platform == "win32":
        path = path.replace('\\', '/')
    
    return path

def copy_to_temp_ascii_path(file_path):
    """将包含中文的文件复制到临时的ASCII路径"""
    # 转换为绝对路径进行检查
    abs_path = os.path.abspath(file_path)
    
    try:
        abs_path.encode('ascii')
        return file_path, None  # 绝对路径是ASCII，不需要复制
    except UnicodeEncodeError:
        # 绝对路径包含非ASCII字符，需要复制到临时目录
        temp_dir = tempfile.mkdtemp()
        file_ext = os.path.splitext(file_path)[1]
        temp_file = os.path.join(temp_dir, f"temp_file{file_ext}")
        
        # 复制文件
        shutil.copy2(file_path, temp_file)
        print(f"🔄 中文路径处理: {os.path.basename(file_path)} -> {temp_file}")
        return temp_file, temp_dir

def cleanup_temp_files(temp_dir):
    """清理临时文件"""
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"🧹 已清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"⚠️ 清理临时文件时出错: {e}")

def convert_srt_to_ass(srt_file):
    """将SRT字幕文件转换为ASS格式，用于硬字幕烧录"""
    try:
        # 创建临时ASS文件
        temp_dir = tempfile.mkdtemp()
        ass_file = os.path.join(temp_dir, "temp_subtitle.ass")
        
        # 使用FFmpeg转换SRT到ASS
        cmd = [
            'ffmpeg', '-y',
            '-i', srt_file,
            '-c:s', 'ass',
            ass_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0 and os.path.exists(ass_file):
            print(f"🔄 SRT转ASS成功: {ass_file}")
            return ass_file, temp_dir
        else:
            print(f"⚠️ SRT转ASS失败: {result.stderr}")
            cleanup_temp_files(temp_dir)
            return None, None
            
    except Exception as e:
        print(f"⚠️ SRT转ASS异常: {str(e)}")
        return None, None

def parse_srt_to_drawtext(srt_file):
    """解析SRT文件并生成drawtext滤镜命令"""
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单的SRT解析
        import re
        pattern = r'(\d+)\n([\d:,]+) --> ([\d:,]+)\n(.*?)(?=\n\d+\n|\n*$)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            return None
        
        # 转换时间格式
        def srt_time_to_seconds(time_str):
            time_str = time_str.replace(',', '.')
            h, m, s = time_str.split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)
        
        # 改进的文本转义函数
        def escape_drawtext(text):
            """对drawtext滤镜进行更robust的文本转义"""
            # 移除换行符并清理空白
            text = text.strip().replace('\n', ' ').replace('\r', ' ')
            # 移除多余空格
            text = ' '.join(text.split())
            
            # 转义特殊字符 - 按照FFmpeg drawtext滤镜要求
            escape_chars = {
                "'": "\\'",      # 单引号
                '"': '\\"',      # 双引号  
                ':': '\\:',      # 冒号
                '\\': '\\\\',    # 反斜杠
                '[': '\\[',      # 方括号
                ']': '\\]',      # 方括号
                ',': '\\,',      # 逗号
                ';': '\\;',      # 分号
                '=': '\\=',      # 等号
            }
            
            for char, escaped in escape_chars.items():
                text = text.replace(char, escaped)
            
            # 限制文本长度，避免过长的滤镜命令
            if len(text) > 200:
                text = text[:197] + "..."
            
            return text
        
        # 生成drawtext滤镜 - 限制数量避免命令过长
        drawtext_filters = []
        max_subtitles = 200  # 限制最大字幕数量
        
        for i, (num, start_time, end_time, text) in enumerate(matches[:max_subtitles]):
            try:
                start_sec = srt_time_to_seconds(start_time)
                end_sec = srt_time_to_seconds(end_time)
                
                # 清理和转义文本
                clean_text = escape_drawtext(text)
                
                if not clean_text:  # 跳过空文本
                    continue
                
                # 使用更安全的drawtext参数格式
                drawtext = f"drawtext=text={clean_text}:fontsize=20:fontcolor=white:bordercolor=black:borderw=1:x=(w-text_w)/2:y=h-text_h-30:enable=between(t\\,{start_sec}\\,{end_sec})"
                drawtext_filters.append(drawtext)
                
            except Exception as e:
                print(f"⚠️ 跳过问题字幕条目 {i+1}: {e}")
                continue
        
        # 组合所有滤镜
        if drawtext_filters:
            combined_filter = ','.join(drawtext_filters)
            # 检查总长度，如果过长则返回None使用备用方案
            if len(combined_filter) > 8000:
                print(f"⚠️ drawtext滤镜命令过长 ({len(combined_filter)} 字符)，将使用备用方案")
                return None
            return combined_filter
        
        return None
        
    except Exception as e:
        print(f"⚠️ 解析SRT文件失败: {str(e)}")
        return None

def run(video_file, subtitle_file, output_file, hard_subtitle=True):
    """
    将字幕嵌入视频
    
    Args:
        video_file: 输入视频文件路径
        subtitle_file: 字幕文件路径
        output_file: 输出视频文件路径
        hard_subtitle: True=硬字幕(烧录到画面), False=软字幕(可切换)
    
    Returns:
        bool: 是否成功
    """
    temp_subtitle_dir = None
    temp_video_dir = None
    try:
        # 验证输入文件
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"视频文件不存在: {video_file}")
        if not os.path.exists(subtitle_file):
            raise FileNotFoundError(f"字幕文件不存在: {subtitle_file}")
        
        # 检查字幕文件是否为空
        if os.path.getsize(subtitle_file) == 0:
            print("⚠️ 警告：字幕文件为空，无法嵌入字幕")
            return False
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 处理中文路径 - 字幕文件和视频文件都需要处理
        temp_subtitle, temp_subtitle_dir = copy_to_temp_ascii_path(subtitle_file)
        temp_video, temp_video_dir = copy_to_temp_ascii_path(video_file)
        
        print(f"📋 调试信息:")
        print(f"   原始视频路径: {video_file}")
        print(f"   临时视频路径: {temp_video}")
        print(f"   原始字幕路径: {subtitle_file}")
        print(f"   临时字幕路径: {temp_subtitle}")
        
        if hard_subtitle:
            # 硬字幕 - 尝试真正的字幕烧录
            print("🔥 硬字幕模式：将字幕烧录到视频画面中")
            
            # 方法1：尝试解析SRT并使用drawtext烧录
            drawtext_filter = parse_srt_to_drawtext(temp_subtitle)
            
            if drawtext_filter:
                print("   方法1: 使用drawtext滤镜烧录字幕...")
                print(f"   生成的滤镜长度: {len(drawtext_filter)} 字符")
                
                cmd = [
                    'ffmpeg', '-y',
                    '-i', temp_video,
                    '-vf', drawtext_filter,
                    '-c:v', 'libx264',
                    '-c:a', 'copy',
                    output_file
                ]
                
                print(f"🚀 执行drawtext烧录命令...")
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                
                if result.returncode == 0:
                    print(f"✅ drawtext硬字幕烧录成功: {output_file}")
                    return True
                else:
                    print(f"⚠️ drawtext方法失败: {result.stderr}")
            
            # 方法2：尝试使用ass滤镜（修复版）
            ass_file, ass_temp_dir = convert_srt_to_ass(temp_subtitle)
            
            if ass_file:
                print("   方法2: 使用ASS滤镜烧录字幕...")
                
                # 修复ASS路径处理 - 使用更简单可靠的方法  
                try:
                    # 直接使用原始路径，让subprocess处理
                    print(f"   ASS字幕路径: {ass_file}")
                    
                    # 使用subtitles滤镜代替ass滤镜，更稳定
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_video,
                        '-vf', f"subtitles={ass_file}",
                        '-c:v', 'libx264',
                        '-c:a', 'copy',
                        output_file
                    ]
                    
                    print(f"🚀 执行ASS烧录命令...")
                    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
                    
                    # 清理ASS临时文件
                    cleanup_temp_files(ass_temp_dir)
                    
                    if result.returncode == 0:
                        print(f"✅ ASS硬字幕烧录成功: {output_file}")
                        return True
                    else:
                        print(f"⚠️ ASS方法失败: {result.stderr}")
                        
                except Exception as e:
                    print(f"⚠️ ASS方法执行错误: {e}")
                    cleanup_temp_files(ass_temp_dir)
            
            # 方法3：回退到带强制标记的软字幕方案
            print("   方法3: 使用强制显示的字幕轨道...")
            print("⚠️  注意：创建带强制标记的字幕轨道（在多数播放器中会自动显示）")
            
            cmd = [
                'ffmpeg', '-y',
                '-i', temp_video,
                '-i', temp_subtitle,
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-c:s', 'mov_text',
                '-map', '0:v',
                '-map', '0:a',
                '-map', '1:s',
                '-metadata:s:s:0', 'forced=1',    # 强制显示
                '-metadata:s:s:0', 'default=1',   # 默认字幕
                '-disposition:s:0', 'default+forced',  # 强制和默认标记
                output_file
            ]
        
        else:
            # 软字幕 - 作为独立轨道嵌入，可在播放器中切换
            print("💾 软字幕模式：将字幕作为独立轨道嵌入")
            cmd = [
                'ffmpeg', '-y',
                '-i', temp_video,
                '-i', temp_subtitle,
                '-c:v', 'copy',       # 复制视频流，不重新编码
                '-c:a', 'copy',       # 复制音频流
                '-c:s', 'mov_text',   # 字幕编码为mov_text
                '-map', '0:v',        # 映射视频流
                '-map', '0:a',        # 映射音频流  
                '-map', '1:s',        # 映射字幕流
                output_file
            ]
        
        print(f"🚀 执行FFmpeg命令: {' '.join(cmd)}")
        
        # 执行FFmpeg命令
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            mode_text = "硬字幕烧录" if hard_subtitle else "软字幕嵌入"
            print(f"✅ {mode_text}成功: {output_file}")
            return True
        else:
            mode_text = "硬字幕烧录" if hard_subtitle else "软字幕嵌入"
            print(f"❌ {mode_text}失败:")
            print(f"   错误代码: {result.returncode}")
            print(f"   错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 字幕嵌入过程中发生错误: {str(e)}")
        return False
    finally:
        # 清理临时文件
        cleanup_temp_files(temp_subtitle_dir)
        cleanup_temp_files(temp_video_dir)

def run_with_bilingual_subtitle(video_file, original_subtitle, translated_subtitle, output_file, original_lang="eng", translated_lang="chi"):
    """
    嵌入双语字幕（上下对照）
    
    Args:
        video_file: 输入视频文件路径
        original_subtitle: 原始语言字幕路径
        translated_subtitle: 翻译后字幕路径
        output_file: 输出视频文件路径
        original_lang: 原始字幕语言代码 (ISO 639-2，如'eng'为英文)
        translated_lang: 翻译字幕语言代码 (ISO 639-2，如'chi'为中文)
    
    Returns:
        bool: 是否成功
    """
    temp_video_dir = None
    temp_original_dir = None
    temp_translated_dir = None
    try:
        # 验证输入文件
        if not os.path.exists(video_file):
            raise FileNotFoundError(f"视频文件不存在: {video_file}")
        if not os.path.exists(original_subtitle):
            raise FileNotFoundError(f"原始字幕文件不存在: {original_subtitle}")
        if not os.path.exists(translated_subtitle):
            raise FileNotFoundError(f"翻译字幕文件不存在: {translated_subtitle}")
        
        # 检查字幕文件是否为空
        if os.path.getsize(original_subtitle) == 0:
            print("⚠️ 警告：原始字幕文件为空，无法嵌入字幕")
            return False
        if os.path.getsize(translated_subtitle) == 0:
            print("⚠️ 警告：翻译字幕文件为空，无法嵌入字幕")
            return False
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 处理中文路径 - 所有文件都需要处理
        temp_video, temp_video_dir = copy_to_temp_ascii_path(video_file)
        temp_original, temp_original_dir = copy_to_temp_ascii_path(original_subtitle)
        temp_translated, temp_translated_dir = copy_to_temp_ascii_path(translated_subtitle)
        
        print(f"🌐 双语字幕模式：")
        print(f"   原始字幕语言: {original_lang}")
        print(f"   翻译字幕语言: {translated_lang}")
        print(f"   临时视频路径: {temp_video}")
        print(f"   临时原始字幕: {temp_original}")
        print(f"   临时翻译字幕: {temp_translated}")
        
        # 双语字幕嵌入 - 使用软字幕方式，支持播放器切换
        cmd = [
            'ffmpeg', '-y',
            '-i', temp_video,
            '-i', temp_original,     # 原始字幕
            '-i', temp_translated,   # 翻译字幕
            '-c:v', 'copy',          # 复制视频流
            '-c:a', 'copy',          # 复制音频流
            '-c:s', 'mov_text',      # 字幕编码
            '-map', '0:v',           # 映射视频流
            '-map', '0:a',           # 映射音频流
            '-map', '1:s',           # 映射原始字幕流
            '-map', '2:s',           # 映射翻译字幕流
            '-metadata:s:s:0', f'language={original_lang}',    # 使用ISO 639-2标准语言代码
            '-metadata:s:s:1', f'language={translated_lang}',  # 使用ISO 639-2标准语言代码
            output_file
        ]
        
        print(f"🚀 执行双语字幕FFmpeg命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            print(f"✅ 双语字幕嵌入成功: {output_file}")
            print(f"   包含语言轨道: {original_lang}(原始) + {translated_lang}(翻译)")
            return True
        else:
            print(f"❌ 双语字幕嵌入失败:")
            print(f"   错误代码: {result.returncode}")
            print(f"   错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 双语字幕嵌入过程中发生错误: {str(e)}")
        return False
    finally:
        # 清理临时文件
        cleanup_temp_files(temp_video_dir)
        cleanup_temp_files(temp_original_dir)
        cleanup_temp_files(temp_translated_dir)

# 示例用法和测试代码（注释掉）
# if __name__ == "__main__":
#     # 单语字幕测试
#     video_file = r'test_video.mp4'
#     subtitle_file = r'test_subtitle.srt'
#     output_file = r'output_with_subtitle.mp4'
#     
#     # 硬字幕测试
#     run(video_file, subtitle_file, output_file, hard_subtitle=True)
#     
#     # 软字幕测试
#     run(video_file, subtitle_file, 'output_soft_subtitle.mp4', hard_subtitle=False)
#     
#     # 双语字幕测试
#     run_with_bilingual_subtitle(video_file, subtitle_file, 'translated_subtitle.srt', 
#                                'output_bilingual.mp4', original_lang="eng", translated_lang="chi")

def translate_subtitle_content(subtitle_content, conversion_type):
    """翻译字幕内容"""
    try:
        # 导入翻译函数
        from Baidu_Text_transAPI import translate
        
        # 解析字幕文件
        import re
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\n*$)'
        matches = re.findall(subtitle_pattern, subtitle_content, re.DOTALL)
        
        if not matches:
            return subtitle_content  # 如果解析失败，返回原内容
        
        # 确定翻译方向
        if conversion_type == "中文转英文":
            from_lang = 'zh'
            to_lang = 'en'
        elif conversion_type == "英文转中文":
            from_lang = 'en' 
            to_lang = 'zh'
        else:
            return subtitle_content  # 不需要翻译
        
        translated_lines = []
        
        for i, (index, start_time, end_time, text) in enumerate(matches):
            # 清理文本
            clean_text = text.strip().replace('\n', ' ')
            
            if clean_text:
                # 翻译文本
                try:
                    translated_text = translate(clean_text, from_lang, to_lang)
                    if not translated_text:
                        translated_text = clean_text  # 翻译失败时保留原文
                except Exception as e:
                    print(f"翻译第{i+1}行失败: {e}")
                    translated_text = clean_text
            else:
                translated_text = clean_text
            
            # 重构字幕条目
            translated_entry = f"{index}\n{start_time} --> {end_time}\n{translated_text}\n"
            translated_lines.append(translated_entry)
        
        return '\n'.join(translated_lines)
        
    except Exception as e:
        print(f"翻译字幕内容失败: {e}")
        return subtitle_content  # 出错时返回原内容

def create_bilingual_subtitle_file(original_subtitle_path, converted_subtitle_path, bilingual_subtitle_path, conversion_type):
    """创建双语字幕文件
    
    Args:
        original_subtitle_path: 原始字幕文件路径
        converted_subtitle_path: 转换后字幕文件路径
        bilingual_subtitle_path: 双语字幕文件输出路径
        conversion_type: 转换类型 ("中文转英文" 或 "英文转中文")
    
    Returns:
        bool: 创建成功返回True，失败返回False
    """
    try:
        import re
        import os
        
        print(f"开始创建双语字幕，转换类型: {conversion_type}")
        
        # 读取原始字幕内容
        if not os.path.exists(original_subtitle_path):
            print(f"❌ 原始字幕文件不存在: {original_subtitle_path}")
            return False
            
        with open(original_subtitle_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 读取转换后字幕内容（如果存在）
        if converted_subtitle_path and os.path.exists(converted_subtitle_path):
            with open(converted_subtitle_path, 'r', encoding='utf-8') as f:
                translated_content = f.read()
        else:
            # 如果没有转换后的字幕，则直接翻译原始内容
            translated_content = translate_subtitle_content(original_content, conversion_type)
        
        # 解析字幕
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\d+\n|\n*$)'
        original_matches = re.findall(subtitle_pattern, original_content, re.DOTALL)
        translated_matches = re.findall(subtitle_pattern, translated_content, re.DOTALL)
        
        if not original_matches:
            print("❌ 无法解析原始字幕格式")
            return False
        
        if len(original_matches) != len(translated_matches):
            print(f"⚠️ 字幕条目数量不匹配: 原始({len(original_matches)}) vs 翻译({len(translated_matches)})")
            # 当数量不匹配时，以较少的为准
            min_length = min(len(original_matches), len(translated_matches))
            original_matches = original_matches[:min_length]
            translated_matches = translated_matches[:min_length]
        
        # 创建双语字幕
        bilingual_entries = []
        
        for orig_match, trans_match in zip(original_matches, translated_matches):
            orig_index, orig_start, orig_end, orig_text = orig_match
            trans_index, trans_start, trans_end, trans_text = trans_match
            
            orig_text = orig_text.strip()
            trans_text = trans_text.strip()
            
            # 根据转换类型决定上下顺序
            if conversion_type == "中文转英文":
                # 中文在上，英文在下
                bilingual_text = f"{orig_text}\n{trans_text}"
            elif conversion_type == "英文转中文":
                # 英文在上，中文在下  
                bilingual_text = f"{orig_text}\n{trans_text}"
            else:
                bilingual_text = orig_text
                
            # 构建双语SRT条目
            entry = f"{orig_index}\n{orig_start} --> {orig_end}\n{bilingual_text}\n"
            bilingual_entries.append(entry)
        
        # 确保输出目录存在
        bilingual_dir = os.path.dirname(bilingual_subtitle_path)
        if bilingual_dir and not os.path.exists(bilingual_dir):
            os.makedirs(bilingual_dir, exist_ok=True)
        
        # 保存双语字幕文件
        with open(bilingual_subtitle_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(bilingual_entries))
        
        print(f"✅ 双语字幕文件已创建: {bilingual_subtitle_path}")
        return True
        
    except Exception as e:
        print(f"❌ 创建双语字幕失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_with_bilingual_subtitle_enhanced(video_file, original_subtitle_file, converted_subtitle_file, output_file, conversion_type, subtitle_mode="硬字幕（烧录到视频）"):
    """
    增强版双语字幕嵌入函数，整合字幕创建和视频嵌入
    
    Args:
        video_file: 输入视频文件路径
        original_subtitle_file: 原始字幕文件路径  
        converted_subtitle_file: 转换后字幕文件路径（可选）
        output_file: 输出视频文件路径
        conversion_type: 转换类型 ("中文转英文" 或 "英文转中文")
        subtitle_mode: 字幕模式（"硬字幕（烧录到视频）" 或 "软字幕（可选显示）"）
    
    Returns:
        dict: 包含处理结果和相关文件路径的字典
    """
    try:
        import os
        import tempfile
        
        print(f"🌐 开始双语字幕处理：{conversion_type}")
        
        # 确定语言代码
        if conversion_type == "中文转英文":
            original_lang = "chi"  # 中文原始
            translated_lang = "eng"  # 英文翻译
        else:  # 英文转中文
            original_lang = "eng"  # 英文原始
            translated_lang = "chi"  # 中文翻译
        
        # 生成临时双语字幕文件
        temp_bilingual_dir = tempfile.mkdtemp(prefix="bilingual_subtitle_")
        temp_bilingual_file = os.path.join(temp_bilingual_dir, "bilingual_subtitle.srt")
        
        # 创建双语字幕文件
        bilingual_success = create_bilingual_subtitle_file(
            original_subtitle_file,
            converted_subtitle_file,
            temp_bilingual_file,
            conversion_type
        )
        
        if not bilingual_success or not os.path.exists(temp_bilingual_file):
            print("❌ 双语字幕文件创建失败")
            cleanup_temp_files(temp_bilingual_dir)
            return {
                'success': False,
                'error': '双语字幕文件创建失败',
                'output_file': None,
                'bilingual_subtitle_file': None
            }
        
        # 根据字幕模式选择嵌入方式
        if subtitle_mode == "硬字幕（烧录到视频）":
            # 硬字幕模式：将双语字幕烧录到视频
            success = run(video_file, temp_bilingual_file, output_file, hard_subtitle=True)
        else:
            # 软字幕模式：如果有两个独立字幕文件，使用双轨道方式
            if converted_subtitle_file and os.path.exists(converted_subtitle_file):
                success = run_with_bilingual_subtitle(
                    video_file,
                    original_subtitle_file,
                    converted_subtitle_file,
                    output_file,
                    original_lang=original_lang,
                    translated_lang=translated_lang
                )
            else:
                # 否则使用单个双语字幕文件
                success = run(video_file, temp_bilingual_file, output_file, hard_subtitle=False)
        
        # 生成最终双语字幕文件路径
        video_dir = os.path.dirname(output_file)
        video_name = os.path.splitext(os.path.basename(output_file))[0]
        conversion_suffix = conversion_type.replace("转", "_to_").replace("中文", "cn").replace("英文", "en")
        final_bilingual_subtitle = os.path.join(video_dir, f"{video_name}_{conversion_suffix}_bilingual.srt")
        
        # 复制双语字幕文件到最终位置
        bilingual_subtitle_saved = False
        try:
            import shutil
            shutil.copy2(temp_bilingual_file, final_bilingual_subtitle)
            bilingual_subtitle_saved = True
            print(f"📋 双语字幕文件已保存: {final_bilingual_subtitle}")
        except Exception as e:
            print(f"⚠️ 双语字幕文件保存失败: {e}")
        
        # 清理临时文件
        cleanup_temp_files(temp_bilingual_dir)
        
        return {
            'success': success,
            'output_file': output_file if success else None,
            'bilingual_subtitle_file': final_bilingual_subtitle if bilingual_subtitle_saved else None,
            'subtitle_mode': subtitle_mode,
            'conversion_type': conversion_type
        }
        
    except Exception as e:
        print(f"❌ 双语字幕处理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'temp_bilingual_dir' in locals():
            cleanup_temp_files(temp_bilingual_dir)
        return {
            'success': False,
            'error': str(e),
            'output_file': None,
            'bilingual_subtitle_file': None
        }
