import os
import subprocess

# 删除音频
def del_audio(video_file, save_file):
    # video_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\En_New.mp4'
    video_file = video_file.replace("\\", '/')
    # if os.path.exists('./videoWithoutAudio.mp4'):
    #     os.remove('./demo.mp3')
    cmd = 'ffmpeg.exe -i ' + video_file + ' -an ' + save_file + '/' + 'videoWithoutAudio.mp4'
    subprocess.call(cmd)
    # video_without_sound = os.path.dirname(video_file) + '/videoWithoutAudio.mp4'
    video_without_sound = save_file + '/videoWithoutAudio.mp4'
    return video_without_sound


# 添加音频
# audio_file = r'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Audio\En.mp3'
# cmd = 'ffmpeg.exe -i videoWithoutAudio.mp4 -i ' + audio_file + ' -c copy -map 0:v:0 -map 1:a:0 newVideo.mp4'
# subprocess.call(cmd)

# 删除临时文件
# cmd = 'del videoWithoutAudio.mp4'
# subprocess.call(cmd)

# print('替换完成')

