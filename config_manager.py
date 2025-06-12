# -*- coding: utf-8 -*-
"""
配置管理模块
统一管理API配置和应用设置
"""

import json
import os
from typing import Dict, Any

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "api": {
                "xunfei": {
                    "appid": "",
                    "api_key": "",
                    "api_secret": ""
                },
                "baidu": {
                    "appid": "",
                    "app_key": ""
                }
            },
            "voice": {
                "speed": 100,
                "volume": 80,
                "voice_type": "xiaoyan"
            },
            "output": {
                "quality": "high",
                "format": "mp4",
                "bitrate": "128k"
            },
            "app": {
                "theme": "light",
                "language": "zh_CN",
                "auto_save": True,
                "log_level": "info"
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置
                    self._merge_config(default_config, loaded_config)
                    return default_config
            else:
                return default_config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return default_config
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]):
        """递归合并配置"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
    
    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key_path: str, default=None):
        """获取配置值，支持点号分隔的路径"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value):
        """设置配置值，支持点号分隔的路径"""
        keys = key_path.split('.')
        config = self.config
        
        # 导航到目标位置
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
    
    def get_api_config(self, api_name: str) -> Dict[str, str]:
        """获取指定API的配置"""
        return self.get(f"api.{api_name}", {})
    
    def set_api_config(self, api_name: str, config: Dict[str, str]):
        """设置指定API的配置"""
        self.set(f"api.{api_name}", config)
    
    def get_voice_config(self) -> Dict[str, Any]:
        """获取语音配置"""
        return self.get("voice", {})
    
    def set_voice_config(self, config: Dict[str, Any]):
        """设置语音配置"""
        for key, value in config.items():
            self.set(f"voice.{key}", value)
    
    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.get("output", {})
    
    def set_output_config(self, config: Dict[str, Any]):
        """设置输出配置"""
        for key, value in config.items():
            self.set(f"output.{key}", value)
    
    def validate_api_config(self) -> Dict[str, bool]:
        """验证API配置是否完整"""
        result = {}
        
        # 验证科大讯飞配置
        xunfei_config = self.get_api_config("xunfei")
        result["xunfei"] = all([
            xunfei_config.get("appid"),
            xunfei_config.get("api_key"),
            xunfei_config.get("api_secret")
        ])
        
        # 验证百度配置
        baidu_config = self.get_api_config("baidu")
        result["baidu"] = all([
            baidu_config.get("appid"),
            baidu_config.get("app_key")
        ])
        
        return result
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到指定文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从指定文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 合并导入的配置
            self._merge_config(self.config, imported_config)
            return True
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.config = self.load_config()

# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷函数
def get_config(key_path: str, default=None):
    """获取配置值"""
    return config_manager.get(key_path, default)

def set_config(key_path: str, value):
    """设置配置值"""
    config_manager.set(key_path, value)

def save_config():
    """保存配置"""
    return config_manager.save_config()

def get_xunfei_config():
    """获取科大讯飞API配置"""
    return config_manager.get_api_config("xunfei")

def get_baidu_config():
    """获取百度API配置"""
    return config_manager.get_api_config("baidu")

def get_voice_config():
    """获取语音配置"""
    return config_manager.get_voice_config()

def validate_api_config():
    """验证API配置"""
    return config_manager.validate_api_config()

if __name__ == "__main__":
    # 测试配置管理器
    cm = ConfigManager()
    
    # 设置一些测试值
    cm.set("api.xunfei.appid", "test_appid")
    cm.set("voice.speed", 120)
    
    # 获取值
    print("科大讯飞APPID:", cm.get("api.xunfei.appid"))
    print("语音速度:", cm.get("voice.speed"))
    
    # 验证API配置
    print("API配置验证:", cm.validate_api_config())
    
    # 保存配置
    cm.save_config()
    print("配置已保存") 