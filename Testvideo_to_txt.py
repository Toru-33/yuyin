# coding=gbk
import voice_get_text
import datetime
video_path=input("音频路径：").replace("\\",'/')
print("开始处理...请等待")
api = voice_get_text.RequestApi(appid="dece0a1f", secret_key="5c48172c37e755de387fd067d15f2505",
                             upload_file_path=video_path)
myresult=api.all_api_request()
def get_format_time(time_long):
    def format_number(num):
        if len(str(num))>1:
            return str(num)
        else:
            return "0"+str(num)
    myhour=0
    mysecond=int(time_long/1000)
    myminute=0
    mymilsec=0
    if mysecond<1:
        return "00:00:00,%s"%(time_long)
    else:
        if mysecond>60:
            myminute=int(mysecond/60)
            if myminute>60:
                myhour=int(myminute/60)
                myminute=myminute-myhour*60
                mysecond=mysecond-myhour*3600-myminute*60
                mymilsec=time_long-1000*(mysecond+myhour*3600+myminute*60)
                return "%s:%s:%s,%s"%(format_number(myhour),format_number(myminute),format_number(mysecond),\
                                      format_number(mymilsec))
            else:
                mysecond=int(mysecond-myminute*60)
                mymilsec=time_long-1000*(mysecond+myminute*60)
                return "00:%s:%s,%s"%(format_number(myminute),format_number(mysecond),format_number(mymilsec))
        else:
            mymilsec=time_long-mysecond*1000
            return "00:00:%s,%s"%(mysecond,mymilsec)
myresult_str=myresult["data"]
myresult_sp=myresult_str.split("},{")
myresult_sp=myresult_sp[1:-1]
myword=""
flag_num=0
for i in myresult_sp:
    flag_num+=1
    print(i)
    word=[]
    key=[]
    a=i.split(",")
    for j in a:
        temp=j.split(":")
        key.append(temp[0][1:-1])
        word.append(temp[1][1:-1])
    get_dic=dict(zip(key,word))
    print(get_dic)
    bg= get_format_time(int(get_dic["bg"]))
    ed= get_format_time(int(get_dic["ed"]))
    real_word=get_dic["onebest"]
    newword=str(flag_num)+"\n"+bg+" --> "+ed+'\n'+real_word+"\n\n\n"
    myword=myword+newword
print(myword)
# myword=video_path.split("/")[-1]+"\n"+myword
nowTime_str = datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H-%M-%S')
path_file=r"./%s.srt"%(nowTime_str)
f = open(path_file,'a')
f.write(myword)
f.write('\n')
f.close()
print('已经识别完成，见输出目录下的srt文件')
input()
