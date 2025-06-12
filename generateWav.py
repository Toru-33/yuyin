import os
import subprocess

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import AudioFileClip

def videoToWav(videoPath,savePath):
    # datanames = os.listdir(videopath)
    # # print(datanames)
    #
    # # 生成mp3文件
    # for i in datanames:
    #     # print(os.path.splitext(i)[1])
    #     if os.path.splitext(i)[1]=='.mp4':
    #         video = VideoFileClip(videopath + '/' + i)
    #         audio = video.audio
    #         audio.write_audiofile(audiopath + '/' + os.path.splitext(i)[0] + '.wav')

    newWav = AudioFileClip(videoPath)
    newWav.write_audiofile(savePath + '/' + 'sound.wav')


def changeCoding(wavPath):
    # for file in os.listdir(input_path):
    #     file1 = input_path + file
    #     file2 = output_path + file
    #     cmd = "ffmpeg -i " + file1 + " -ar 16000 -ac 1 " + file2  # ffmpeg -i 输入文件 -ar 采样率 -ac 通道数 输出文件
    #     subprocess.call(cmd, shell=True)
    # 提取文件名和扩展名
    file_name, file_ext = os.path.splitext(wavPath)

    # 设置输出文件路径
    output_path = file_name + "_changed" + file_ext
    cmd = "ffmpeg -i " + wavPath + " -ar 16000 -ac 1 " + output_path  # ffmpeg -i 输入文件 -ar 采样率 -ac 通道数 输出文件
    subprocess.call(cmd, shell=True)

def run(videoPath, savePath):
    videoToWav(videoPath, savePath)
    wavPath = savePath + '/' + 'sound.wav'
    changeCoding(wavPath)
    return wavPath
# videopath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Video/'
# audiopath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Sound/'
#
# splitPath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Sound\SplitSound/'
# changedPath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Sound\ChangedSound/'
#
# videoToWav(videopath, audiopath)

# changeCoding(splitPath, changedPath)
