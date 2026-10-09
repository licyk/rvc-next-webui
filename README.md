<div align="center">

# RVC Next WebUI

_[RVC Next](https://github.com/licyk/rvc-next) 一键启动器_

</div>

- [简介](#简介)
- [安装](#安装)
  - [方式一: 整合包安装 (仅支持 Windows)](#方式一-整合包安装-仅支持-windows)
  - [方式二: 手动安装 (支持全平台)](#方式二-手动安装-支持全平台)
    - [准备](#准备)
    - [下载并启动](#下载并启动)
- [启动参数](#启动参数)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 简介

RVC Next WebUI 会自动完成 RVC Next 的运行环境配置并启动 WebUI:

1. 检查 PyTorch, 未安装时根据显卡 (NVIDIA / AMD / Intel) 和系统自动安装对应版本的 PyTorch
2. 检查并安装 `requirements.txt` 中的依赖 (包括 RVC Next)
3. 启动 RVC Next WebUI, 并在浏览器中打开

所有数据 (设置, 数据库, 模型, 实验和输出) 保存在项目的 `data` 文件夹中, Python 环境保存在 `venv` 文件夹中。

## 安装

### 方式一: 整合包安装 (仅支持 Windows)

此方式仅支持 Windows, 下载整合包并解压后即可按照整合包说明使用。

1. 打开 [SD WebUI All In One 项目](https://github.com/licyk/sd-webui-all-in-one)的 README, 找到并点击 **SD WebUI All In One 文档** 链接。
2. 在文档中依次点击 **整合包与实用指南** → **整合包下载与使用**。
3. 在该页面中找到 **RVC Next WebUI** 的说明。
4. 点击 RVC Next WebUI 说明中的整合包下载按钮, 下载整合包并解压, 然后按照该说明启动和使用。

### 方式二: 手动安装 (支持全平台)

此方式支持 Windows、Linux 和 macOS。

#### 准备

安装以下软件:

- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads/) 3.10 及以上版本 (Windows 上安装时勾选 `Add python.exe to PATH`)

#### 下载并启动

使用 Git 下载项目:

```bash
git clone https://github.com/licyk/rvc-next-webui
cd rvc-next-webui
```

然后运行启动脚本:

| 系统 | 启动方式 |
| --- | --- |
| Windows | 双击 `start.bat`, 或在 PowerShell 中运行 `./start.ps1` |
| Linux / macOS | 在终端中运行 `./start.sh` |

首次启动时会创建虚拟环境并下载 PyTorch 和 RVC Next, 需要等待一段时间。之后再运行启动脚本即可直接启动。

## 启动参数

启动参数可以直接加在启动脚本后面, 如 `./start.sh --port 7870 --no-browser`。

| 参数 | 说明 |
| --- | --- |
| `--data-dir <路径>` | RVC Next 数据目录 (默认为项目中的 `data` 文件夹) |
| `--config-dir <路径>` | 保存 `settings.toml` 的目录 (默认为数据目录) |
| `--host <地址>` | 监听地址 (默认为 `127.0.0.1`), 非本机地址需要同时设置 `--access-token` |
| `--port <端口>` | 监听端口 (默认为 `7868`), 端口被占用时尝试下一个端口 |
| `--strict-port` | 端口被占用时直接退出 |
| `--access-token <令牌>` | 访问令牌 |
| `--api-prefix <路径>` | 将 API 和 WebUI 挂载到指定路径下, 如 `/voice` |
| `--no-browser` | 启动后不自动打开浏览器 |
| `--share` | 使用 Gradio 内网穿透生成公网访问地址 (有效期 72 小时), 未设置 `--access-token` 时自动生成访问令牌并显示在日志中 |
| `--proxy <地址>` | 手动指定代理地址, 如 `http://127.0.0.1:7890` (默认自动读取系统代理) |
| `--disable-proxy` | 禁用自动设置代理 |
| `--skip-check` | 跳过运行环境的依赖检查 |
| `--torch-backend <类型>` | 安装 PyTorch 时使用的类型: `auto` (默认), `cuda`, `rocm`, `xpu`, `mps`, `cpu` |
| `--reinstall-torch` | 重新安装 PyTorch, 可与 `--torch-backend` 一起使用 |
| `--index-url <地址>` | 安装项目依赖时使用的 PyPI 镜像 (不影响 PyTorch 的安装) |
| `--debug` | 启用 Debug 日志 |
| `--version` | 显示版本信息 |

## 常见问题

**自动选择的 PyTorch 类型不正确**

使用 `--reinstall-torch --torch-backend <类型>` 重新安装 PyTorch, 如 `./start.sh --reinstall-torch --torch-backend cuda`。

**NVIDIA 显卡使用了 CPU 版本的 PyTorch**

CUDA 13.0 版本的 PyTorch 需要 580 及以上版本的显卡驱动, 驱动过旧时会依次回退到 CUDA 12.8 / 12.6 版本, 更旧的驱动只能使用 CPU 版本。更新显卡驱动后使用 `--reinstall-torch` 重新安装 PyTorch。

**代理设置**

启动时会在检查依赖前自动设置代理: 使用 `--proxy` 指定的代理; 未指定时使用环境变量 `HTTP_PROXY` / `HTTPS_PROXY` 中已有的代理; 都没有时读取系统代理 (Windows 系统设置, Linux 的 GNOME / KDE 设置, macOS 系统设置), 能连接到代理服务器时才会使用。系统代理为 SOCKS 代理时不会自动使用, 请使用 `--proxy` 指定 HTTP 代理。不需要代理时使用 `--disable-proxy` 禁用。

**Linux 上无法使用实时变声**

实时变声需要系统的 PortAudio 库, Debian / Ubuntu 上使用 `sudo apt install libportaudio2` 安装。

更多使用说明请参考 [RVC Next 文档](https://github.com/licyk/rvc-next)。

## 许可证

本项目使用 [GNU General Public License v3.0](LICENSE) (GPL-3.0) 发布。你可以在 GPL-3.0 条款下使用、复制、修改和分发本项目; 分发修改版本时, 请遵守 GPL-3.0 的源代码开放和许可证保留要求。
