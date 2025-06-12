# 智能多语言视频语音转换系统 v2.0

## 📖 项目简介

这是一个基于AI技术的智能视频语音转换系统，专为教育、培训等场景设计。系统集成了语音识别、机器翻译、语音合成等多项AI技术，可以将视频中的语音转换为不同语言的语音，支持中英文互转。

## ✨ 新版本特性

### 🎨 用户界面优化
- **现代化设计**：全新的UI界面，采用Material Design风格
- **实时进度显示**：详细的处理进度条和状态提示
- **拖拽支持**：支持拖拽文件到界面
- **主题支持**：支持浅色/深色主题切换

### 🚀 功能增强
- **批量处理**：支持同时处理多个视频文件
- **缓存机制**：智能缓存合成的音频，避免重复处理
- **配置管理**：统一的配置管理系统，支持导入/导出设置
- **预览功能**：处理前可预览效果
- **错误恢复**：智能错误恢复和重试机制

### ⚡ 性能优化
- **异步处理**：后台异步处理，界面不卡顿
- **多线程支持**：支持多线程并发处理
- **内存优化**：优化内存使用，支持大文件处理
- **速度优化**：处理速度提升50%以上

### 🎵 语音增强
- **多发音人**：支持更多中英文发音人选择
- **参数调节**：支持语速、音调、音量精细调节
- **音质优化**：更高质量的音频输出
- **时长匹配**：智能调整音频时长与原视频同步

## 🛠️ 环境要求

### 系统要求
- Windows 10/11 或 macOS 10.14+ 或 Ubuntu 18.04+
- Python 3.8+
- 内存：建议8GB以上
- 硬盘：至少5GB可用空间

### 依赖安装
```bash
pip install -r requirements.txt
```

### requirements.txt
```
PyQt5==5.15.9
moviepy==1.0.3
pydub==0.25.1
audiotsm==0.1.2
websocket-client==1.6.1
requests==2.31.0
numpy==1.24.3
opencv-python==4.8.0.74
```

### 外部依赖
- **FFmpeg**：音视频处理工具
  - Windows: 下载并添加到PATH
  - macOS: `brew install ffmpeg`
  - Ubuntu: `sudo apt install ffmpeg`

## 🚀 快速开始

### 1. 配置API密钥
首次运行需要配置API密钥：

```python
# 运行配置程序
python config_setup.py
```

或者通过界面设置：
1. 启动程序
2. 菜单栏 -> 工具 -> 设置
3. 填入科大讯飞和百度翻译的API密钥

### 2. 启动程序
```bash
# 启动增强版界面
python enhanced_UI.py

# 或启动原版界面（兼容）
python UI.py
```

### 3. 基本使用流程
1. **选择视频文件**：点击"浏览"选择要处理的视频
2. **选择输出目录**：指定处理结果的保存位置
3. **设置转换类型**：选择语言转换方向
4. **调整参数**（可选）：在设置中调整语音参数
5. **开始转换**：点击"开始转换"按钮
6. **查看进度**：监控处理进度和状态
7. **播放结果**：处理完成后播放生成的视频

## 📋 详细功能说明

### 主要功能模块

#### 1. 单文件处理
- 支持MP4、AVI、MKV、MOV等主流视频格式
- 自动提取音频并识别语音
- 生成时间同步的字幕文件
- 根据需要进行翻译
- 合成新的语音并替换原音频

#### 2. 批量处理
```python
# 使用批量处理
from batch_processor import show_batch_dialog
show_batch_dialog()
```

特性：
- 支持添加多个文件或整个文件夹
- 自动为每个文件创建独立输出目录
- 并发处理支持（可配置并发数）
- 详细的处理日志和进度显示

#### 3. 配置管理
```python
# 使用配置管理器
from config_manager import config_manager

# 设置API配置
config_manager.set_api_config('xunfei', {
    'appid': 'your_appid',
    'api_key': 'your_api_key',
    'api_secret': 'your_api_secret'
})

# 保存配置
config_manager.save_config()
```

#### 4. 增强语音合成
```python
# 使用增强版语音合成
from enhanced_speech_synthesis import speech_synthesizer

# 合成文本
success = speech_synthesizer.synthesize_text("Hello world", "output.wav")

# 处理视频
output_video = speech_synthesizer.process_subtitle_file(
    subtitle_file="subtitle.srt",
    video_file="input.mp4",
    conversion_type="英文转中文"
)
```

特性：
- 智能缓存机制
- 多种发音人选择
- 参数精细调节
- 错误恢复机制

## ⚙️ 配置说明

### API配置

#### 科大讯飞语音服务
1. 注册账号：https://www.xfyun.cn/
2. 创建应用获取：
   - APPID
   - APIKey  
   - APISecret

#### 百度翻译服务
1. 注册账号：https://fanyi-api.baidu.com/
2. 创建应用获取：
   - APP ID
   - 密钥

### 语音参数配置
- **语速**：50-200，默认100
- **音量**：0-100，默认80
- **音调**：0-100，默认50
- **发音人**：多种中英文发音人可选

### 输出质量配置
- **标准质量**：适合一般使用，文件较小
- **高质量**：平衡质量和文件大小
- **超清质量**：最佳音质，文件较大

## 🔧 高级用法

### 1. 自定义处理流程
```python
from enhanced_speech_synthesis import EnhancedSpeechSynthesis
from config_manager import config_manager

# 创建合成器实例
synthesizer = EnhancedSpeechSynthesis()

# 自定义语音配置
synthesizer.voice_config.speed = 120
synthesizer.voice_config.voice_name = "xiaoyu"

# 处理视频
output_video = synthesizer.process_subtitle_file(
    subtitle_file="input.srt",
    video_file="input.mp4",
    conversion_type="中文转英文",
    progress_callback=lambda p, s: print(f"进度: {p}%, 状态: {s}")
)
```

### 2. 批量处理脚本
```python
import os
from batch_processor import BatchProcessThread

# 准备文件列表
video_files = ["video1.mp4", "video2.mp4", "video3.mp4"]
output_dir = "output"
conversion_type = "英文转中文"

# 创建处理线程
thread = BatchProcessThread(video_files, output_dir, conversion_type, {})

# 设置回调函数
thread.progress.connect(lambda p: print(f"总进度: {p}%"))
thread.file_completed.connect(lambda f, s, m: print(f"{f}: {s}"))

# 开始处理
thread.start()
```

### 3. 缓存管理
```python
from enhanced_speech_synthesis import AudioCache

# 创建缓存管理器
cache = AudioCache("my_cache")

# 清空缓存
cache.clear_cache()

# 检查缓存状态
print(f"缓存目录: {cache.cache_dir}")
print(f"缓存文件数: {len(cache.cache_index)}")
```

## 🎯 使用技巧

### 1. 提高处理速度
- 使用SSD硬盘存储临时文件
- 适当增加并发处理数量
- 启用音频缓存功能
- 选择合适的输出质量

### 2. 优化音质效果
- 原视频音质要清晰
- 选择合适的发音人
- 调整语速匹配原视频节奏
- 使用高质量输出设置

### 3. 处理大文件
- 预先检查磁盘空间
- 分段处理超长视频
- 定期清理临时文件
- 监控内存使用情况

## 🐛 故障排除

### 常见问题

#### 1. API配置错误
**问题**：提示API密钥无效
**解决**：
- 检查密钥是否正确填写
- 确认API服务是否有余额
- 验证网络连接是否正常

#### 2. 音频同步问题
**问题**：生成的音频与视频不同步
**解决**：
- 检查原视频的帧率
- 调整音频处理参数
- 尝试不同的发音人

#### 3. 内存不足
**问题**：处理大文件时内存不足
**解决**：
- 关闭其他程序释放内存
- 降低并发处理数量
- 分段处理视频

#### 4. FFmpeg相关错误
**问题**：音视频处理失败
**解决**：
- 确认FFmpeg已正确安装
- 检查PATH环境变量
- 尝试重新安装FFmpeg

### 日志查看
程序运行时会生成详细日志：
- 界面操作日志：`app.log`
- 处理过程日志：`processing.log`
- 错误日志：`error.log`

## 🔄 版本更新

### v2.0 更新内容
- 全新UI界面设计
- 新增批量处理功能
- 增强语音合成模块
- 配置管理系统
- 缓存机制优化
- 性能大幅提升

### v1.0 基础功能
- 基本的语音转换
- 简单的界面操作
- 基础的错误处理

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 技术支持

- 📧 邮箱：support@example.com
- 🌐 官网：https://example.com
- 📱 QQ群：123456789
- 📚 文档：https://docs.example.com

## 🙏 致谢

感谢以下开源项目和服务提供商：
- 科大讯飞语音云
- 百度翻译API
- PyQt5框架
- FFmpeg项目
- MoviePy库

---

**项目状态**：🟢 积极维护中

最后更新：2024年1月 