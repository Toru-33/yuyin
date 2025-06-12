import json

# 给定的字典
data_dict = {'data': '[{"bg":"0","ed":"1310","onebest":" Hello, everyone. ","speaker":"0"},{"bg":"1310","ed":"3040","onebest":"My name is Xiao yan. ","speaker":"0"}]'}

# 获取键为 'data' 的值
json_string = data_dict['data']

# 解析 JSON 字符串
data_list = json.loads(json_string)

# 输出解析后的数据
print(type(data_list))
print(data_list)
print(type(data_list[0]))
print(str(data_list))
print(type(str(data_list)))