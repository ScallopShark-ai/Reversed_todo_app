# 逆序打卡 (Reverse Clock)

> 一个极简的、基于“逆序倒计时”理念的习惯养成工具。
>
> *Every day counts. Make them count backwards to zero.*

![App Screenshot](image_53f5bd.png)

## 📖 简介 (Introduction)

**逆序打卡** 是一款基于 Python 和 Flet 框架开发的跨平台打卡应用（目前主要适配 Android）。与传统的“累计天数”打卡软件不同，本应用采用**倒计时机制**。

你需要为每一个习惯设定一个“目标天数”（例如：坚持跑步 30 天）。每次打卡，天数减一；如果当天未打卡，天数不减反增（惩罚机制），直到数字归零，任务才算真正完成并进入成就墙。这种“减法”机制能带来更强的紧迫感和目标达成后的释放感。

## ✨ 核心功能 (Features)

* **📉 逆序倒计时**：
    * 设定目标天数（如 30 天），每完成一次打卡，距离目标就近一步。
    * **视觉激励**：
        * 剩余 > 10 天：黑色（平稳期）
        * 剩余 5 - 10 天：<span style="color:blue">**蓝色**</span>（冲刺期）
        * 剩余 < 5 天：<span style="color:green">**绿色**</span>（胜利在望）
* **⚖️ 自动惩罚机制 (Smart Penalty)**：
    * 基于“懒加载”算法。应用启动时自动检测上次活跃时间。
    * 若**昨天**未打卡，再次打开应用时，剩余天数会自动 **+1**。
    * 若**连续多天**未打开应用，漏掉的天数将全部累加作为惩罚。
* **🏆 成就墙 (Achievement Wall)**：
    * 当任务倒计时归零时，任务卡片自动移入成就墙。
    * 永久记录任务名称、目标天数以及**实际耗时周期**（创建日期 - 完成日期），直观展示你的毅力。
* **📱 移动端适配**：
    * 专为手机操作优化，大字体、大按钮，单手即可轻松完成打卡。
    * 完美居中的卡片 UI 设计。
* **💾 本地安全存储**：
    * 利用 `ClientStorage` 技术，数据仅保存在用户设备本地，无需联网，保护隐私。

## 🛠️ 技术栈 (Tech Stack)

* **语言**: [Python 3.11+](https://www.python.org/)
* **UI 框架**: [Flet](https://flet.dev/) (基于 Google Flutter)
* **打包工具**: GitHub Actions (自动构建 Android APK)

## 🚀 快速开始 (Getting Started)

### 方式一：直接安装 (Android)

前往本仓库的 [Releases 页面](#) 下载最新的 `.apk` 安装包，发送到手机并安装即可。

### 方式二：本地运行 (开发调试)

如果你想在电脑上运行或修改代码：

1.  **克隆仓库**
    ```bash
    git clone [https://github.com/your-username/reverse-clock.git](https://github.com/your-username/reverse-clock.git)
    cd reverse-clock
    ```

2.  **安装依赖**
    ```bash
    pip install flet
    ```

3.  **运行应用**
    ```bash
    # 电脑端预览
    python main.py

    # 手机端预览 (需手机安装 Flet App 并在同一 WiFi 下)
    flet run main.py --android
    ```

## 📂 项目结构

```text
reverse-clock/
├── main.py            # 程序主入口 (包含所有 UI 和 逻辑)
├── msyh.ttc           # 微软雅黑字体 (用于解决中文显示问题)
├── icon.png           # 应用图标
├── requirements.txt   # 依赖清单
└── .github/           # GitHub Actions 自动打包脚本
