"""RVC Next WebUI 配置"""

import logging
import os
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
"""项目根目录"""

DATA_PATH = ROOT_PATH / "data"
"""RVC Next 数据目录 (设置, 数据库, 模型, 输出和缓存)"""

REQUIREMENTS_PATH = ROOT_PATH / "requirements.txt"
"""依赖记录文件路径"""

LOGGER_NAME = os.getenv("RVC_NEXT_WEBUI_LOGGER_NAME", "RVC-Next-WebUI")
"""日志器名称"""

LOGGER_LEVEL = int(os.getenv("RVC_NEXT_WEBUI_LOGGER_LEVEL", str(logging.INFO)))
"""日志等级"""

LOGGER_COLOR = os.getenv("RVC_NEXT_WEBUI_LOGGER_COLOR", "1").lower() not in {"0", "false", "none"}
"""是否启用彩色日志"""

DEFAULT_SERVER_HOST = "127.0.0.1"
"""默认监听地址"""

DEFAULT_SERVER_PORT = 7868
"""默认监听端口 (与 rvc-next 默认端口一致)"""

TORCH_MIN_VERSION = "2.7.1"
"""RVC Next 需要的最低 PyTorch 版本"""

PYTORCH_INDEX_URL = "https://download.pytorch.org/whl"
"""PyTorch 官方软件包索引"""

PYTORCH_INSTALL_ARGS: dict[str, list[str]] = {
    "cuda": ["torch==2.14.0", "--index-url", f"{PYTORCH_INDEX_URL}/cu130"],
    "cuda128": [f"torch>={TORCH_MIN_VERSION}", "--index-url", f"{PYTORCH_INDEX_URL}/cu128"],
    "cuda126": [f"torch>={TORCH_MIN_VERSION}", "--index-url", f"{PYTORCH_INDEX_URL}/cu126"],
    "rocm": ["torch[device-all]==2.13.0+rocm10.0.0", "--index-url", "https://stable.repo.amd.com/rocm/whl-next"],
    "xpu": ["torch==2.14.0+xpu", "--index-url", f"{PYTORCH_INDEX_URL}/xpu"],
    "mps": ["torch==2.14.0"],
    "cpu": ["torch==2.14.0", "--index-url", f"{PYTORCH_INDEX_URL}/cpu"],
}
"""各 PyTorch 类型的 Pip 安装参数

命令来自 rvc-next 文档 (installation): cuda / rocm / xpu / mps / cpu

- cuda128 / cuda126: 驱动不支持 CUDA 13.0 (驱动版本低于 580) 时的回退类型, 不固定 PyTorch 版本

未提供 DirectML: torch-directml (0.2.5.dev240914) 依赖 torch==2.4.1, 与 rvc-next 需要的 torch>=2.7.1 冲突
"""

TORCH_BACKEND_CHOICES = ["auto", "cuda", "rocm", "xpu", "mps", "cpu"]
"""命令行可选的 PyTorch 类型"""
