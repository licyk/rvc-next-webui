"""运行环境检查

分为两个阶段:

1. PyTorch: 未安装 (或版本低于 RVC Next 的要求) 时根据显卡类型和系统安装对应的 PyTorch
2. 项目依赖: 检查 requirements.txt 中的依赖 (包括 rvc-next) 及 rvc-next 自身声明的依赖, 缺失时进行安装
"""

import importlib
import os
import sys

from rvc_next_webui.cmd_runner import run_cmd
from rvc_next_webui.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
    PYTORCH_INSTALL_ARGS,
    REQUIREMENTS_PATH,
    TORCH_MIN_VERSION,
)
from rvc_next_webui.gpu_detector import detect_torch_backend
from rvc_next_webui.logger import get_logger
from rvc_next_webui.package_analyzer import (
    is_package_installed,
    validate_package_metadata_dependencies,
    validate_requirements,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

TORCH_REQUIREMENT = f"torch>={TORCH_MIN_VERSION}"
"""RVC Next 需要的 PyTorch 版本"""


def pip_install(
    *args: str,
) -> None:
    """使用当前 Python 解释器的 Pip 安装 Python 软件包

    Args:
        *args (str):
            传递给 ``pip install`` 的参数

    Raises:
        RuntimeError:
            安装失败时
    """
    custom_env = os.environ.copy()
    custom_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    run_cmd([sys.executable, "-m", "pip", "install", *args], custom_env=custom_env, shell=False)
    importlib.invalidate_caches()


def check_pytorch(
    backend: str = "auto",
    reinstall: bool = False,
) -> None:
    """检查 PyTorch, 未安装时根据显卡类型安装

    Args:
        backend (str):
            PyTorch 类型, ``auto`` 为自动检测
        reinstall (bool):
            卸载已安装的 PyTorch 并重新安装

    Raises:
        RuntimeError:
            PyTorch 安装失败时
    """
    logger.info("检查 PyTorch 中")
    if reinstall:
        logger.info("卸载原有 PyTorch 中")
        run_cmd([sys.executable, "-m", "pip", "uninstall", "torch", "-y"], shell=False, check=False)
        importlib.invalidate_caches()
    elif is_package_installed(TORCH_REQUIREMENT):
        logger.info("PyTorch 已安装")
        return
    elif is_package_installed("torch"):
        logger.warning("已安装的 PyTorch 版本低于 RVC Next 需要的 %s, 将重新安装 PyTorch", TORCH_MIN_VERSION)

    if backend == "auto":
        backend = detect_torch_backend()
    logger.info("安装 PyTorch 中, 类型: %s", backend)

    pip_install(*PYTORCH_INSTALL_ARGS[backend])
    if not is_package_installed(TORCH_REQUIREMENT):
        raise RuntimeError("PyTorch 安装后仍未满足版本要求, 请检查上方的 Pip 输出")
    logger.info("PyTorch 安装完成")


def _requirements_satisfied() -> bool:
    """检查项目依赖及 rvc-next 自身声明的依赖是否完整

    Returns:
        bool:
            依赖完整时返回 True
    """
    if not validate_requirements(REQUIREMENTS_PATH):
        return False
    # requirements.txt 只记录顶层依赖, rvc-next 的依赖缺失 / 损坏时也需要重新安装
    return validate_package_metadata_dependencies("rvc-next")


def check_requirements(
    index_url: str | None = None,
) -> None:
    """检查项目依赖, 缺失时进行安装

    Args:
        index_url (str | None):
            安装依赖时使用的 PyPI 镜像地址

    Raises:
        FileNotFoundError:
            依赖记录文件不存在时
        RuntimeError:
            依赖安装失败时
    """
    if not REQUIREMENTS_PATH.is_file():
        raise FileNotFoundError(f"在 {REQUIREMENTS_PATH} 中未找到依赖记录文件, 请检查项目文件是否完整")

    logger.info("检查 RVC Next WebUI 依赖中")
    if _requirements_satisfied():
        logger.info("RVC Next WebUI 依赖完整")
        return

    logger.info("安装 RVC Next WebUI 依赖中")
    args = ["-r", REQUIREMENTS_PATH.as_posix()]
    if index_url:
        args += ["--index-url", index_url]
    pip_install(*args)
    if not _requirements_satisfied():
        raise RuntimeError("RVC Next WebUI 依赖安装后仍不完整, 请检查上方的 Pip 输出")
    logger.info("RVC Next WebUI 依赖安装完成")


def check_environment(
    backend: str = "auto",
    reinstall_torch: bool = False,
    index_url: str | None = None,
) -> None:
    """依次检查 PyTorch 和项目依赖

    Args:
        backend (str):
            PyTorch 类型, ``auto`` 为自动检测
        reinstall_torch (bool):
            重新安装 PyTorch
        index_url (str | None):
            安装项目依赖时使用的 PyPI 镜像地址

    Raises:
        FileNotFoundError:
            依赖记录文件不存在时
        RuntimeError:
            依赖安装失败时
    """
    check_pytorch(backend=backend, reinstall=reinstall_torch)
    check_requirements(index_url=index_url)
