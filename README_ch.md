# ARIA v2

[English Version](README.md)

<p align="center">
  <strong>AI Realtime Intelligent Audio (AI 实时智能音频)</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey.svg" alt="Windows">
  <img src="https://img.shields.io/badge/license-GPLv3-blue.svg" alt="GPLv3 License">
</p>
**Windows 平台通用的实时 AI 字幕工具** - 使用 AI 语音识别技术捕获并转录系统上播放的任何音频。

<img width="860" height="700" alt="PixPin_2026-02-19_05-25-50" src="https://github.com/user-attachments/assets/5cb7e9c9-8016-41ad-b4b2-a6d63e3bdbe9" />

## 功能特性

### 核心功能
- **通用音频捕获** - 兼容任何应用程序（游戏、视频、通话等）。
- **三种识别模式**:
  - **精确模式 (Precise)**: 使用 Whisper 进行高精度转写（推荐使用 NVIDIA GPU）。
  - **实时模式 (Realtime)**: 使用 Sherpa-ONNX / Vosk 进行逐词流式转写（CPU 或 GPU）。
  - **实时字幕模式 (LiveCaptions)**: 使用 Windows 11 内置 AI（✅ **无需 GPU/CUDA**，支持 AMD / Intel / NVIDIA）。
- **多语言支持**: 中文、英文、日文、韩文等。
- **实时翻译**: 使用 Google Cloud 或 NLLB（本地）对转录内容进行翻译。
- **自定义悬浮窗**: 可拖动、可自由调整位置的字幕窗。
- **多语言界面**: 英文、繁体中文、简体中文。
- **内置 Python 环境**: 无需单独安装 Python。

### 新增更新与优化(v2.0.1)

> [!IMPORTANT]
> **更新方法:** 直接使用本项目的 `src` 文件夹替换您原项目整合包中的 `src` 文件夹即可。

- **增加麦克风输入**: 自动识别音频输入设备，并加入音频来源下拉列表。
- **`.ts` 文件尾随转写**: 支持对一个不断增长的 `.ts` 文件进行游标尾随实时转写（1:1 速度）。每次循环对所选文件夹进行扫描，自动追读最新 `.ts` 文件的增长部分。采用缓存算法跳过头部不稳定的部分并保持安全时间。可选择是否扫描子文件夹。
- **S3 云盘支持**: 可自动上传到 S3 云盘并生成直链进行访问。
- **时区设置**: 增加时区设置，可以控制日志里和控制台的时区显示。
- **字幕悬浮窗控制**: 增加快速关闭和开启字幕悬浮窗的按钮。
- **日志管理优化**: 
  - 增加切换详细日志和简要日志的开关（简要日志仅显示时间和转写/翻译的内容）。
  - 日志和控制台里的转写内容均完整显示，不再截断。
  - 日志改为即写即落盘，不会锁定文件。
- **繁简体分离**: 将中文简体和中文繁体区分开，解决了输出内容繁简混杂的问题。
- **界面 (UI) 优化**: 优化了 UI 布局，显示项不会拥挤在一起，且可以随意改变 UI 窗口的大小。
- **一键启动脚本**: 可以绕过前端界面，直接启动程序。

## 系统要求

### 🟢 ARIA 极速版 (Lite，推荐)
**适合绝大多数用户，开箱即用，零配置。**
*   **操作系统**: Windows 11 (22H2 或更高版本)
*   **硬件**: 任何标准的笔记本或台式机 (Intel / AMD / NVIDIA)
*   **无需特定的 GPU 或 CUDA 支持。**

---

### 🔷 ARIA 完整版 (Full / 离线版)
**适合需要离线高精度转写的用户。**

*   **操作系统**: Windows 10 或 11
*   **GPU**: 推荐 NVIDIA GTX 10 系列或更新版本以获得最佳速度
*   **存储空间**: 约 10 GB 可用空间

## 下载

### 选择您的版本

| 版本 | 大小 | 描述 | Google Drive | 百度网盘 |
|---------|------|-------------|--------------|-----------------------------|
| **极速版 (Lite)** 【推荐】 | ~600 MB | **适合大多数用户。** 轻量、快速、准确，支持任意显卡 (AMD/Intel)。**需要 Windows 11 (22H2 或更高版本)。** | [Google Drive](https://drive.google.com/drive/folders/1rRQrj0IPX7rnQxA30WvmxhH-5c6fWZa8?usp=drive_link) | [百度网盘](https://pan.baidu.com/s/1KkSlAv7X5yi90hTYuWZoPQ?pwd=j5ip) |
| **完整版 (Full)** | ~7.6 GB | 包含所有模式 (精确/实时/系统实时字幕)。已预装离线模型。 | [Google Drive](https://drive.google.com/drive/folders/1rdxunARIa3-68VV4xAKlbzh_dv_wI130?usp=drive_link) | [百度网盘](https://pan.baidu.com/s/1yGc-pU6DdPFw8po60ubI3w?pwd=r2m6) |

### 完整版内置模型

| 模型 | 类型 | 大小 | 支持语言 |
|-------|------|------|-----------|
| Whisper Large-v3 | 精确模式 | 3 GB | 所有语言 |
| Sherpa-ONNX 双语版 | 实时模式 | 500 MB | 中文, 英文 |
| Vosk 日文版 | 实时模式 | 1 GB | 日文 |
| NLLB 翻译模型 | 翻译 | 1.2 GB | 多种语言 |

## 快速开始

1. 下载并解压 ZIP 文件。
2. 双击运行 **`ARIA.bat`**。
3. **极速版 (Lite)**: 启动后即可直接使用 (仅包含实时字幕模式)。
4. **完整版 (Full)**: 在界面上选择识别模式，然后点击 **开始 (Start)**。

## 配置说明

### 识别模式

| 模式 | 引擎 | 最佳适用场景 | GPU 需求 |
|------|--------|----------|----------------|
| **精确模式 (Precise)** | Whisper | 演讲、视频、预录制内容 | 推荐使用 NVIDIA 显卡 |
| **实时模式 (Realtime)** | Sherpa-ONNX / Vosk | 实时对话、直播流 | CPU / GPU |
| **实时字幕模式 (LiveCaptions)** | Windows 11 AI | **日常通用 (看电影/开会)** | ✅ 任何 CPU / GPU (不需要 NPU) |

### 支持语言

| 语言 | 精确模式 | 实时模式 | 实时字幕模式 (LiveCaptions) |
|----------|--------------|---------------|------------------|
| 中文 | ✅ | ✅ (Sherpa-ONNX) | ✅ |
| 英文 | ✅ | ✅ (Sherpa-ONNX) | ✅ |
| 日文 | ✅ | ✅ (Vosk) | ✅ |
| 韩文 | ✅ | ❌ | ✅ |
| 西班牙文, 法文等 | ✅ | ❌ | ✅ |
| 其余 50+ 种语言 | ✅ | ❌ | ❌ |

> **实时字幕模式**: 依托 Windows 11 内置 AI 支持 11 种语言。无需额外下载模型！

### 翻译功能

**本地模型 (离线使用):**
- **NLLB-200**: Meta 开源的多语言翻译模型，支持 200 多种语言，完全本地运行。

**在线服务 (免费 API):**
- **Google 翻译**: 快速准确 (基于网页抓取)。
- **Bing 翻译**: 微软提供的翻译服务。
- **有道翻译**: 专门针对中英文互译进行了优化。

>  **注意**: 在线服务通过网页抓取实现，可能会受到请求频率的限制。为了保证稳定性，推荐使用本地的 NLLB 模型。

## 目录结构

```
ARIA/
├── python/          # 内置的 Python 环境 (无需安装)
├── src/             # 源代码
├── models/          # AI 模型文件 (仅限完整版)
├── ARIA.bat         # 启动脚本
```

## 界面截图
<img width="860" height="700" alt="PixPin_2026-02-19_05-25-39" src="https://github.com/user-attachments/assets/173cce11-5af3-4c0b-a2e5-f2f3c5aafa64" />
<img width="1436" height="700" alt="19" src="https://github.com/user-attachments/assets/6088cbb4-62ff-444b-9a79-2e4005a8f4c0" />


## 许可证

本项目基于 **GNU General Public License v3.0** 开源 - 相关细节请查看 [LICENSE](LICENSE) 文件。

## 致谢
- [Faster Whisper](https://github.com/SYSTRAN/faster-whisper)
- [Sherpa-ONNX](https://github.com/k2-fsa/sherpa-onnx)
- [Vosk](https://alphacephei.com/vosk/)
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)

## 联系方式

- GitHub: [@sayksii](https://github.com/sayksii)
- 邮箱: mark42967151@gmail.com
