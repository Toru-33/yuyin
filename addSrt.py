import subprocess
#
# video_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Video\En.mp4'  # 输入视频文件路径
# subtitle_file = r'D\:\\PyCharmProfessional\\PyCharm\\Project\\YuYinTiHuan\\subtitle1.srt'  # 字幕文件路径
# output_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\output.mp4'  # 输出视频文件路径
#
# def run(video_file, subtitle_file, output_file):
#     cmdLine = 'ffmpeg -i "' + video_file + '" -vf "subtitles=\'' + subtitle_file + '\'" "' + output_file + '"'
#     print(cmdLine)
#     subprocess.call(cmdLine, shell=True)
# run(video_file, subtitle_file, output_file)
video_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Video\En.mp4'  # 输入视频文件路径
subtitle_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\subtitle1.srt'  # 字幕文件路径
output_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\output.mp4'  # 输出视频文件路径


def run(video_file, subtitle_file, output_file):
    cmdLine = 'ffmpeg -i "{0}" -vf "subtitles={1}" -c:v libx264 -c:a aac "{2}"'.format(video_file, subtitle_file,
                                                                                       output_file)
    print(cmdLine)
    subprocess.call(cmdLine, shell=True)


# run(video_file, subtitle_file, output_file)
