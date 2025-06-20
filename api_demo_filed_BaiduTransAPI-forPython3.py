#百度垂直领域翻译API,不包含词典、tts语音合成等资源，如有相关需求请联系translate_api@baidu.com
# 2020.07.28 更新，原url拼接错误，感谢热心网友指正
# coding=utf-8

import http.client
import hashlib
import urllib
import random
import json

appid = ''  # 填写你的appid
secretKey = ''  # 填写你的密钥

httpClient = None
myurl = '/api/trans/vip/fieldtranslate'

fromLang = 'auto'   #原文语种
toLang = 'zh'   #译文语种
salt = random.randint(32768, 65536)
q= 'apple'
domain = 'medicine'
sign = appid + q + str(salt) + domain + secretKey
sign = hashlib.md5(sign.encode()).hexdigest()
myurl = myurl + '?appid=' + appid + '&q=' + urllib.parse.quote(q) + '&from=' + fromLang + '&to=' + toLang + '&salt=' + str(salt) + '&domain=' + domain + '&sign=' + sign

try:
    httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
    httpClient.request('GET', myurl)

    # response是HTTPResponse对象
    response = httpClient.getresponse()
    result_all = response.read().decode("utf-8")
    result = json.loads(result_all)

    print (result)

except Exception as e:
    print (e)
finally:
    if httpClient:
        httpClient.close()