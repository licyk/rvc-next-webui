"""代理配置

在依赖检查前读取系统代理并通过环境变量应用, 使 Pip 和 RVC Next 的模型下载都经过代理
"""

import configparser
import os
import re
import socket
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

from rvc_next_webui.cmd_runner import run_cmd
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

PROXY_ENV_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
"""表示已配置代理的环境变量"""

NO_PROXY_HOSTS = ("localhost", "127.0.0.1", "::1")
"""不经过代理的地址, 保证访问本机的 RVC Next 服务器时不走代理"""


def get_windows_proxy_address() -> str | None:
    """获取 Windows 系统上的代理配置

    Returns:
        (str | None):
            代理地址
    """
    import winreg

    winreg = cast(Any, winreg)
    proxy_config_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, proxy_config_path, 0, winreg.KEY_READ) as reg:
            proxy_enable: int = winreg.QueryValueEx(reg, "ProxyEnable")[0]
            proxy_server: str = winreg.QueryValueEx(reg, "ProxyServer")[0]
    except OSError as e:
        logger.debug("获取 Windows 上的代理地址出现错误: %s", e)
        return None

    if proxy_enable != 1:
        return None

    # 匹配 http 或 https 的情况
    http_match = re.search(r"(?:http|https)=([^;]+)", proxy_server)
    if http_match:
        proxy_value = http_match.group(1)
        # 去除可能存在的协议前缀并统一加 http://
        proxy_value = proxy_value.replace("http://", "").replace("https://", "")
        return f"http://{proxy_value}"

    #  匹配 socks 的情况
    socks_match = re.search(r"socks=([^;]+)", proxy_server)
    if socks_match:
        proxy_value = socks_match.group(1)
        # 去除前缀并加 socks://
        proxy_value = proxy_value.replace("http://", "").replace("https://", "").replace("socks://", "")
        return f"socks://{proxy_value}"

    # 直接是 IP:PORT 形式
    # 先清理掉可能存在的简单协议头
    clean_value = proxy_server.replace("http://", "").replace("https://", "").replace("socks://", "")
    return f"http://{clean_value}"


def get_linux_proxy_address() -> str | None:
    """获取 Linux 系统上的代理配置

    依次读取 Gnome (gsettings) 和 KDE (~/.config/kioslaverc) 的代理配置

    Returns:
        (str | None):
            代理地址
    """
    try:
        mode = (run_cmd(["gsettings", "get", "org.gnome.system.proxy", "mode"], live=False) or "").strip().replace("'", "").replace('"', "")
        if mode == "manual":
            http_host = (
                (run_cmd(["gsettings", "get", "org.gnome.system.proxy.http", "host"], live=False) or "")
                .strip()
                .replace("'", "")
                .replace('"', "")
            )
            http_port = (run_cmd(["gsettings", "get", "org.gnome.system.proxy.http", "port"], live=False) or "").strip()
            if http_host and http_port and http_port != "0":
                return f"http://{http_host}:{http_port}"

            socks_host = (
                (run_cmd(["gsettings", "get", "org.gnome.system.proxy.socks", "host"], live=False) or "")
                .strip()
                .replace("'", "")
                .replace('"', "")
            )
            socks_port = (run_cmd(["gsettings", "get", "org.gnome.system.proxy.socks", "port"], live=False) or "").strip()
            if socks_host and socks_port and socks_port != "0":
                return f"socks://{socks_host}:{socks_port}"
    except RuntimeError as e:
        logger.debug("获取 Linux (Gnome) 上的代理地址出现错误: %s", e)

    kde_config_path = Path("~/.config/kioslaverc").expanduser()
    config = configparser.ConfigParser(interpolation=None)
    if not kde_config_path.is_file():
        return None

    try:
        with open(kde_config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 构造一个虚拟的头部来包裹那些不在 section 里的配置项项
        fake_content = "[GLOBAL]\n" + content
        config.read_string(fake_content)

        # 检查目标节 [Proxy Settings]
        section_name = "Proxy Settings"
        if not config.has_section(section_name):
            return None

        section = config[section_name]

        # ProxyType=1 代表手动代理
        if section.get("ProxyType") != "1":
            return None

        # 获取代理配置
        # 依次尝试 httpProxy, httpsProxy, socksProxy
        raw_proxy = section.get("httpProxy") or section.get("httpsProxy") or section.get("socksProxy")
        if not raw_proxy:
            return None

        # 判断最终应该返回的协议头
        if section.get("httpProxy") or section.get("httpsProxy"):
            target_proto = "http"
        else:
            target_proto = "socks"

        # 格式化地址 (处理 "http://127.0.0.1 10808" 这种带空格的情况)
        # 先去掉协议头
        clean_value = re.sub(r"^(https?|socks)://", "", raw_proxy).strip()
        # 将空格替换为冒号 (127.0.0.1 10808 -> 127.0.0.1:10808)
        clean_value = clean_value.replace(" ", ":")

        if clean_value:
            return f"{target_proto}://{clean_value}"

    except (OSError, configparser.Error) as e:
        logger.warning("获取 Linux (KDE) 上的代理地址出现错误: %s", e)

    return None


def get_macos_proxy_address() -> str | None:
    """获取 MacOS 系统上的代理配置

    Returns:
        (str | None):
            代理地址
    """
    try:
        output = run_cmd(["scutil", "--proxy"], live=False) or ""
    except RuntimeError as e:
        logger.debug("获取 MacOS 上的代理地址出现错误: %s", e)
        return None

    # HTTP 代理
    if re.search(r"HTTPEnable\s+:\s+1", output):
        host = re.search(r"HTTPProxy\s+:\s+(\S+)", output)
        port = re.search(r"HTTPPort\s+:\s+(\d+)", output)
        if host and port:
            return f"http://{host.group(1)}:{port.group(1)}"

    # HTTPS 代理
    if re.search(r"HTTPSEnable\s+:\s+1", output):
        host = re.search(r"HTTPSProxy\s+:\s+(\S+)", output)
        port = re.search(r"HTTPSPort\s+:\s+(\d+)", output)
        if host and port:
            return f"http://{host.group(1)}:{port.group(1)}"

    # SOCKS 代理
    if re.search(r"SOCKSEnable\s+:\s+1", output):
        host = re.search(r"SOCKSProxy\s+:\s+(\S+)", output)
        port = re.search(r"SOCKSPort\s+:\s+(\d+)", output)
        if host and port:
            return f"socks://{host.group(1)}:{port.group(1)}"

    return None


def get_system_proxy_address() -> str | None:
    """获取系统上的代理地址

    Returns:
        (str | None):
            代理地址
    """
    if sys.platform == "win32":
        return get_windows_proxy_address()
    if sys.platform == "linux":
        return get_linux_proxy_address()
    if sys.platform == "darwin":
        return get_macos_proxy_address()

    return None


def test_proxy_connectivity(
    proxy_addr: str,
    timeout: float = 5,
) -> bool:
    """测试代理地址是否可以连通

    Args:
        proxy_addr (str):
            代理地址, 支持 http:// 和 socks:// 协议
        timeout (float):
            超时时间 (秒), 默认为 5 秒

    Returns:
        (bool):
            代理服务器是否可以连通
    """
    try:
        parsed_proxy = urlparse(proxy_addr)
        proxy_host = parsed_proxy.hostname
        proxy_port = parsed_proxy.port
    except ValueError as e:
        logger.debug("代理地址格式不正确: %s, %s", proxy_addr, e)
        return False

    if not proxy_host or not proxy_port:
        logger.debug("代理地址格式不正确: %s", proxy_addr)
        return False

    # 对于所有类型的代理 (HTTP/HTTPS/SOCKS), 都使用 TCP 连接测试代理服务器是否可访问
    try:
        with socket.create_connection((proxy_host, proxy_port), timeout=timeout):
            logger.debug("代理服务器 %s 连接成功", proxy_addr)
            return True
    except OSError as e:
        logger.debug("代理服务器 %s 连接失败: %s", proxy_addr, e)
        return False


def get_env_proxy_address() -> str | None:
    """获取环境变量中已配置的代理地址

    Returns:
        (str | None):
            代理地址, 未配置时返回 None
    """
    for name in PROXY_ENV_NAMES:
        value = os.getenv(name)
        if value:
            return value
    return None


def set_proxy(
    addr: str,
) -> None:
    """通过环境变量配置代理, 并保证访问本机地址时不经过代理

    Args:
        addr (str):
            代理地址
    """
    os.environ["HTTP_PROXY"] = addr
    os.environ["HTTPS_PROXY"] = addr
    set_no_proxy()


def set_no_proxy() -> None:
    """将本机地址加入 NO_PROXY, 保留已有的配置"""
    existing = os.getenv("NO_PROXY") or os.getenv("no_proxy") or ""
    hosts = [h.strip() for h in existing.split(",") if h.strip()]
    hosts += [h for h in NO_PROXY_HOSTS if h not in hosts]
    os.environ["NO_PROXY"] = ",".join(hosts)


def configure_proxy(
    proxy: str | None = None,
    disable: bool = False,
) -> None:
    """配置代理

    优先级: 手动指定的代理 > 环境变量中已有的代理 > 系统代理.
    系统代理需要通过连通性测试才会应用; SOCKS 代理不会自动应用, 因为 Pip 在未安装 PySocks 时无法使用 SOCKS 代理.

    Args:
        proxy (str | None):
            手动指定的代理地址, 优先于自动检测
        disable (bool):
            禁用自动设置代理, 不修改代理相关的环境变量
    """
    if disable:
        logger.info("已禁用自动设置代理")
        return

    if proxy:
        set_proxy(proxy)
        logger.info("使用手动指定的代理: %s", proxy)
        return

    env_proxy = get_env_proxy_address()
    if env_proxy:
        set_no_proxy()
        logger.info("使用环境变量中已配置的代理: %s", env_proxy)
        return

    system_proxy = get_system_proxy_address()
    if system_proxy is None:
        logger.debug("未检测到系统代理")
        return

    if system_proxy.startswith("socks"):
        logger.warning(
            "检测到系统代理 %s 为 SOCKS 代理, Pip 无法直接使用, 跳过自动设置代理. 可使用 --proxy 手动指定 HTTP 代理", system_proxy
        )
        return

    if not test_proxy_connectivity(system_proxy):
        logger.warning("检测到系统代理 %s, 但无法连接到代理服务器, 跳过自动设置代理", system_proxy)
        return

    set_proxy(system_proxy)
    logger.info("检测到系统代理, 已设置代理: %s", system_proxy)
