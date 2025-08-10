try:
    from moviepy.editor import *  # noqa
except Exception:
    pass
import os
from pydub import AudioSegment
from pydub.utils import make_chunks
import subprocess

'''转换MP4文件'''
# 加载文件
def videoToMp3(videopath,audiopath):
    datanames = os.listdir(videopath)
    # print(datanames)

    # 生成mp3文件
    for i in datanames:
        # print(os.path.splitext(i)[1])
        if os.path.splitext(i)[1]=='.mp4':
            video = VideoFileClip(videopath + '/' + i)
            audio = video.audio
            audio.write_audiofile(audiopath + '/' + os.path.splitext(i)[0] + '.mp3')


'''切分wav文件'''
def dividMp3(audiopath, savepath):
    # 加载文件
    audiopath_1 = os.listdir(audiopath)
    # print(audiopath_1)

    for i in audiopath_1:
        if os.path.splitext(i)[1] == '.mp3':
            print(audiopath + i)
            audio = AudioSegment.from_file(audiopath + i, "mp3")

            size = 50000  # 切割的毫秒数 50s=50000

            chunks = make_chunks(audio, size)  # 将文件切割为50s一个
            print(chunks)
            for j, chunk in enumerate(chunks):
                print(chunk)
                chunk_name = os.path.splitext(i)[0] + "_{0}.mp3".format(j)
                print(savepath + chunk_name)
                chunk.export(savepath + chunk_name , format="mp3")

def changeCoding(input_path, output_path):
    for file in os.listdir(input_path):
        file1 = input_path + file
        file2 = output_path + file
        cmd = "ffmpeg -i " + file1 + " -ar 16000 -ac 1 " + file2  # ffmpeg -i 输入文件 -ar 采样率 -ac 通道数 输出文件
        subprocess.call(cmd, shell=True)





videopath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Video/'
audiopath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Sound/'

splitPath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Sound\SplitSound/'
changedPath = 'D:\PyCharmProfessional\PyCharm\Project\YuYinTiHuan\Sound\ChangedSound/'

videoToMp3(videopath, audiopath)
# dividMp3(audiopath, splitPath)
changeCoding(splitPath, changedPath)


