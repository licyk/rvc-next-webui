"""硬件检测

参考 sd-webui-all-in-one 的 pytorch_manager/gpu_detector.py, 仅保留选择 PyTorch 类型所需的部分
"""

import json
import re
import shutil
import subprocess
import sys
from typing import TypedDict

from rvc_next_webui.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from rvc_next_webui.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

_DETECTION_OUTPUT_ERRORS = (ValueError, TypeError, KeyError, IndexError, AttributeError)
"""解析硬件检测工具输出时可能出现的异常 (工具输出格式与预期不符)"""


class GPUDeviceInfo(TypedDict, total=False):
    """显卡信息"""

    Name: str
    """显卡名称"""

    AdapterCompatibility: str | None
    """显卡兼容能力 (类型)"""

    AdapterRAM: str | None
    """显卡显存大小"""

    DriverVersion: str | None
    """驱动版本"""


def _run_detection_command(
    cmd: list[str],
) -> str | None:
    """执行硬件检测命令并返回标准输出

    检测工具不存在是正常情况, 仅记录调试日志; 检测工具存在但执行失败时记录警告,
    避免驱动异常等问题被静默当作 "没有显卡".

    Args:
        cmd (list[str]):
            要执行的命令

    Returns:
        str | None:
            命令的标准输出, 执行失败时返回 None
    """
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        ).stdout
    except FileNotFoundError:
        logger.debug("未找到硬件检测工具: %s", cmd[0])
        return None
    except subprocess.CalledProcessError as e:
        logger.warning("执行硬件检测工具 %s 失败, 退出码: %s, 错误信息: %s", cmd[0], e.returncode, (e.stderr or "").strip())
        return None
    except (OSError, subprocess.SubprocessError) as e:
        logger.warning("执行硬件检测工具 %s 失败: %s", cmd[0], e)
        return None


def get_cuda_version() -> float:
    """获取驱动支持的 CUDA 版本

    Returns:
        float:
            驱动支持的 CUDA 版本, 获取失败时返回 0.0
    """
    output = _run_detection_command(["nvidia-smi", "-q"])
    if output is None:
        return 0.0
    match = re.search(r"CUDA Version\s+:\s+(\d+\.\d+)", output)
    if not match:
        match = re.search(r"CUDA UMD Version\s+:\s+(\d+\.\d+)", output)
    if match:
        return float(match.group(1))
    logger.warning("未能从 nvidia-smi 输出中解析到 CUDA 版本")
    return 0.0


def normalize_gpu_name(
    name: str,
) -> str:
    """规范化 GPU 名称用于匹配

    Args:
        name (str):
            GPU 名称

    Returns:
        str:
            规范化后的 GPU 名称
    """
    return re.sub(r"[^a-z0-9]+", " ", name.casefold()).strip()


def _vendor_of(
    gpu: GPUDeviceInfo,
) -> str:
    """获取规范化后的 GPU 厂商信息

    Args:
        gpu (GPUDeviceInfo):
            GPU 信息

    Returns:
        str:
            小写的厂商信息, 缺失时为空字符串
    """
    return (gpu.get("AdapterCompatibility") or "").casefold()


def _is_amd_vendor(
    vendor: str,
) -> bool:
    """检查厂商信息是否为 AMD

    Args:
        vendor (str):
            小写的 GPU 厂商信息

    Returns:
        bool:
            厂商信息为 AMD 时返回 True
    """
    return "advanced micro devices" in vendor or re.search(r"\b(amd|ati)\b", vendor) is not None


def get_windows_gpu_list() -> list[GPUDeviceInfo]:
    """获取 Windows 上的显卡列表

    Returns:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    cmd = [
        "powershell",
        "-NoLogo",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterCompatibility, AdapterRAM, DriverVersion | ConvertTo-Json",
    ]
    output = _run_detection_command(cmd)
    if not output:
        return []

    try:
        gpus = json.loads(output)
        if isinstance(gpus, dict):
            gpus = [gpus]

        gpu_info: list[GPUDeviceInfo] = []
        for gpu in gpus:
            name = gpu.get("Name")
            if not isinstance(name, str) or not name:
                continue
            gpu_info.append(
                {
                    "Name": name,
                    "AdapterCompatibility": gpu.get("AdapterCompatibility", None),
                    "AdapterRAM": gpu.get("AdapterRAM", None),
                    "DriverVersion": gpu.get("DriverVersion", None),
                }
            )
        return gpu_info
    except _DETECTION_OUTPUT_ERRORS as e:
        logger.warning("解析 Windows 显卡信息失败: %s", e)
        return []


def get_lshw_gpus() -> list[GPUDeviceInfo]:
    """通过 lshw 获取 GPU 信息

    Returns:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if not shutil.which("lshw"):
        return []

    output = _run_detection_command(["lshw", "-C", "display", "-json"])
    if not output:
        return []

    try:
        data = json.loads(output)
        gpus = [data] if isinstance(data, dict) else data

        gpu_info: list[GPUDeviceInfo] = []
        for gpu in gpus:
            gpu_info.append(
                {
                    "Name": gpu.get("product"),
                    "AdapterCompatibility": gpu.get("vendor"),
                    "AdapterRAM": str(gpu.get("size")) if gpu.get("size") else None,
                    "DriverVersion": gpu.get("configuration", {}).get("driver"),
                }
            )
        return gpu_info
    except _DETECTION_OUTPUT_ERRORS as e:
        logger.warning("解析 lshw 显卡信息失败: %s", e)
        return []


def get_nvidia_smi_gpus() -> list[GPUDeviceInfo]:
    """通过 nvidia-smi 获取 NVIDIA 显卡精确信息

    Returns:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if not shutil.which("nvidia-smi"):
        return []

    output = _run_detection_command(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
    if not output:
        return []

    try:
        gpu_info: list[GPUDeviceInfo] = []
        for line in output.strip().splitlines():
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            gpu_info.append(
                {
                    "Name": parts[0],
                    "AdapterCompatibility": "NVIDIA",
                    "AdapterRAM": str(int(parts[1]) * 1024 * 1024) if parts[1].isdigit() else None,
                    "DriverVersion": parts[2],
                }
            )
        return gpu_info
    except _DETECTION_OUTPUT_ERRORS as e:
        logger.warning("解析 nvidia-smi 显卡信息失败: %s", e)
        return []


def get_lspci_gpus() -> list[GPUDeviceInfo]:
    """通过 lspci 获取显卡信息

    同时查询 VGA 控制器 (0300) 和 3D 控制器 (0302), 后者包含没有显示输出的计算卡

    Returns:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    if not shutil.which("lspci"):
        return []

    gpu_info: list[GPUDeviceInfo] = []
    for device_class in ("::0300", "::0302"):
        output = _run_detection_command(["lspci", "-vmm", "-d", device_class])
        if not output:
            continue

        try:
            for dev in output.strip().split("\n\n"):
                info = {line.split(":", 1)[0].strip(): line.split(":", 1)[1].strip() for line in dev.split("\n") if ":" in line}
                name = info.get("Device")
                if not name:
                    continue
                gpu_info.append(
                    {
                        "Name": name,
                        "AdapterCompatibility": info.get("Vendor"),
                        "AdapterRAM": None,
                        "DriverVersion": info.get("Driver"),
                    }
                )
        except _DETECTION_OUTPUT_ERRORS as e:
            logger.warning("解析 lspci 显卡信息失败: %s", e)

    return gpu_info


def get_linux_gpu_list() -> list[GPUDeviceInfo]:
    """获取 Linux 上的显卡列表

    Returns:
        list[GPUDeviceInfo]:
            显卡信息列表
    """
    all_gpus: list[GPUDeviceInfo] = []

    all_gpus.extend(get_nvidia_smi_gpus())
    all_gpus.extend(get_lshw_gpus())
    all_gpus.extend(get_lspci_gpus())

    unique_gpus: dict[str, GPUDeviceInfo] = {}

    for gpu in all_gpus:
        name = gpu.get("Name")
        if not name:
            continue

        norm_name = name.strip().lower()

        if norm_name not in unique_gpus:
            unique_gpus[norm_name] = gpu
        else:
            existing = unique_gpus[norm_name]
            for key in ("AdapterCompatibility", "AdapterRAM", "DriverVersion"):
                if not existing.get(key) and gpu.get(key):
                    existing[key] = gpu[key]

    return list(unique_gpus.values())


def get_gpu_list() -> list[GPUDeviceInfo]:
    """获取当前平台上的 GPU 列表

    Returns:
        list[GPUDeviceInfo]:
            显卡信息列表, macOS 等不支持检测的平台返回空列表
    """
    if sys.platform == "win32":
        return get_windows_gpu_list()
    if sys.platform == "linux":
        return get_linux_gpu_list()
    return []


def has_nvidia_gpu(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含 NVIDIA 显卡

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在 NVIDIA 显卡时则返回 True
    """
    return any("nvidia" in _vendor_of(x) for x in gpu_list)


def has_amd_gpu(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含 AMD 独立显卡 / 计算卡 / Radeon 核显

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在 AMD 显卡时则返回 True
    """
    for gpu in gpu_list:
        if not _is_amd_vendor(_vendor_of(gpu)):
            continue
        name = normalize_gpu_name(gpu.get("Name") or "")
        if "radeon" in name or "instinct" in name or re.search(r"\bmi\d{3}", name) is not None:
            return True
    return False


def has_intel_xpu(
    gpu_list: list[GPUDeviceInfo],
) -> bool:
    """检测 GPU 列表中是否包含支持 XPU 的 Intel 显卡 (Arc 系列 / Core Ultra 核显)

    Windows 上的名称形如 ``Intel(R) Arc(TM) A770 Graphics``, Linux lspci 上形如 ``DG2 [Arc A770]``

    Args:
        gpu_list (list[GPUDeviceInfo]):
            GPU 列表

    Returns:
        bool:
            当列表中存在支持 XPU 的 Intel 显卡时则返回 True
    """
    for gpu in gpu_list:
        if "intel" not in _vendor_of(gpu):
            continue
        name = normalize_gpu_name(gpu.get("Name") or "")
        if re.search(r"\barc\b", name) is not None or "core ultra" in name:
            return True
    return False


def detect_torch_backend(
    gpu_list: list[GPUDeviceInfo] | None = None,
) -> str:
    """检测当前设备适用的 PyTorch 类型

    优先级: NVIDIA (CUDA) > AMD (ROCm) > Intel (XPU) > CPU, macOS 固定使用带 MPS 支持的默认版本.
    NVIDIA 驱动不支持 CUDA 13.0 时回退到 CUDA 12.8 / 12.6, 驱动过旧时使用 CPU 版本.

    Args:
        gpu_list (list[GPUDeviceInfo] | None):
            GPU 列表, 为 None 时自动获取当前平台上的 GPU 列表

    Returns:
        str:
            PyTorch 类型, 为 ``config.PYTORCH_INSTALL_ARGS`` 中的键
    """
    if sys.platform == "darwin":
        return "mps"

    if gpu_list is None:
        gpu_list = get_gpu_list()

    if gpu_list:
        for gpu in gpu_list:
            logger.info("检测到显卡: %s (%s)", gpu.get("Name"), gpu.get("AdapterCompatibility") or "未知厂商")
    else:
        logger.info("未检测到显卡")

    if has_nvidia_gpu(gpu_list):
        cuda_version = get_cuda_version()
        if cuda_version == 0.0:
            logger.warning("无法获取 NVIDIA 驱动支持的 CUDA 版本, 将使用 CUDA 13.0 版本的 PyTorch (需要 580 及以上版本的驱动)")
            return "cuda"
        logger.info("NVIDIA 驱动支持的 CUDA 版本: %s", cuda_version)
        if cuda_version >= 13.0:
            return "cuda"
        if cuda_version >= 12.8:
            logger.warning("NVIDIA 驱动不支持 CUDA 13.0, 将使用 CUDA 12.8 版本的 PyTorch, 建议更新显卡驱动")
            return "cuda128"
        if cuda_version >= 12.6:
            logger.warning("NVIDIA 驱动不支持 CUDA 13.0, 将使用 CUDA 12.6 版本的 PyTorch, 建议更新显卡驱动")
            return "cuda126"
        logger.warning(
            "NVIDIA 驱动版本过旧 (仅支持 CUDA %s), 将使用 CPU 版本的 PyTorch, 请更新显卡驱动后使用 --reinstall-torch 重新安装 PyTorch",
            cuda_version,
        )
        return "cpu"

    if has_amd_gpu(gpu_list):
        return "rocm"

    if has_intel_xpu(gpu_list):
        return "xpu"

    return "cpu"
