# -*- coding: utf-8 -*-

# This code shows an example of text translation from English to Simplified-Chinese.
# This code runs on Python 2.7.x and Python 3.x.
# You may install `requests` to run this code: pip install requests
# Please refer to `https://api.fanyi.baidu.com/doc/21` for complete api document

import requests
import random
import json
from hashlib import md5

# Set your own appid/appkey.
appid = '20240510002047252'
appkey = 'kTWYriLuEEEKr0BE70d1'

endpoint = 'http://api.fanyi.baidu.com'
path = '/api/trans/vip/translate'
url = endpoint + path

# Generate salt and sign
def make_md5(s, encoding='utf-8'):
    return md5(s.encode(encoding)).hexdigest()

def translate(query, from_lang='en', to_lang='zh'):
    """
    翻译文本
    :param query: 要翻译的文本
    :param from_lang: 源语言
    :param to_lang: 目标语言
    :return: 翻译结果
    """
    try:
        # 如果文本为空或过长，直接返回原文
        if not query or len(query) > 10000:
            return query
            
        salt = random.randint(32768, 65536)
        sign = make_md5(appid + query + str(salt) + appkey)

        # Build request
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'appid': appid, 'q': query, 'from': from_lang, 'to': to_lang, 'salt': salt, 'sign': sign}

        # Send request with timeout
        r = requests.post(url, params=payload, headers=headers, timeout=10)
        result = r.json()

        # Check if translation is successful
        if 'trans_result' in result and len(result['trans_result']) > 0:
            translated_text = result['trans_result'][0]['dst']
            print(f"翻译成功: {query} -> {translated_text}")
            return translated_text
        else:
            print(f"翻译失败: {result}")
            return query
            
    except Exception as e:
        print(f"翻译异常: {e}")
        return query

# 测试代码（仅在直接运行时执行）
if __name__ == "__main__":
    test_query = 'From now on， we will get'
    result = translate(test_query, 'en', 'zh')
    print(f"测试翻译结果: {result}")
