"""Gradio 内网穿透

使用 gradio-tunneling 库通过 Gradio 的共享服务器生成公网访问地址 (https://xxx.gradio.live), 有效期为 72 小时.

隧道转发的请求会保留公网地址的 Host 请求头, 且来源地址为 127.0.0.1, 因此:

- 需要将公网地址加入 RVC Next 的 Host 白名单, 否则请求会被防 DNS 重绑定检查拒绝
- RVC Next 会将隧道转发的请求视为本机请求, 必须设置访问令牌
"""

import importlib
import secrets
from typing import Any

from rvc_next_webui.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from rvc_next_webui.env_check import pip_install
from rvc_next_webui.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

GRADIO_TUNNELING_PACKAGE = "gradio-tunneling"
"""Gradio 内网穿透使用的 Python 软件包"""

GRADIO_API_TIMEOUT = 10
"""请求 Gradio API 服务器的超时时间 (秒)"""


def _import_gradio_tunneling(
    index_url: str | None = None,
) -> Any:
    """导入 gradio-tunneling, 未安装时进行安装

    Args:
        index_url (str | None):
            安装时使用的 PyPI 镜像地址

    Returns:
        Any:
            ``gradio_tunneling.main`` 模块

    Raises:
        RuntimeError:
            安装失败时
    """
    try:
        return importlib.import_module("gradio_tunneling.main")
    except ImportError:
        pass

    logger.info("安装 %s 中", GRADIO_TUNNELING_PACKAGE)
    args = [GRADIO_TUNNELING_PACKAGE]
    if index_url:
        args += ["--index-url", index_url]
    pip_install(*args)
    try:
        return importlib.import_module("gradio_tunneling.main")
    except ImportError as e:
        raise RuntimeError(f"{GRADIO_TUNNELING_PACKAGE} 安装后仍无法导入: {e}") from e


def allow_extra_hosts() -> set[str]:
    """让之后创建的 RVC Next 应用接受额外的 Host 请求头, 需要在启动 RVC Next 服务器前调用

    RvcNextServer 没有提供 Host 白名单参数, 因此替换 ``create_app`` 传入一个由调用方持有的集合,
    启动内网穿透后再将公网地址的主机名加入该集合.

    Returns:
        set[str]:
            额外允许的 Host 集合, 向其中添加的主机名会立即生效
    """
    import rvc_next.api.app as app_module

    # SecurityMiddleware 会将空集合替换为新的集合, 预先放入本来就允许的 localhost 使其保留该集合的引用
    hosts = {"localhost"}
    create_app = app_module.create_app

    def _create_app(*args: Any, **kwargs: Any) -> Any:
        kwargs["extra_hosts"] = hosts
        return create_app(*args, **kwargs)

    setattr(app_module, "create_app", _create_app)
    return hosts


def generate_access_token() -> str:
    """生成随机访问令牌

    Returns:
        str:
            访问令牌
    """
    return secrets.token_urlsafe(16)


class GradioTunnel:
    """Gradio 内网穿透"""

    def __init__(
        self,
        port: int,
        index_url: str | None = None,
    ) -> None:
        """初始化 Gradio 内网穿透

        Args:
            port (int):
                要进行端口映射的本地端口
            index_url (str | None):
                安装 gradio-tunneling 时使用的 PyPI 镜像地址
        """
        self.port = port
        self.index_url = index_url
        self._tunnel: Any = None
        self._url: str | None = None

    def start(
        self,
    ) -> str:
        """启动 Gradio 内网穿透

        Returns:
            str:
                公网访问地址

        Raises:
            RuntimeError:
                启动失败时
        """
        logger.info("启动 Gradio 内网穿透中")
        gradio_tunneling = _import_gradio_tunneling(self.index_url)
        import requests

        try:
            response = requests.get(gradio_tunneling.GRADIO_API_SERVER, timeout=GRADIO_API_TIMEOUT)
            response.raise_for_status()
            payload = response.json()[0]
            remote_host, remote_port = payload["host"], int(payload["port"])
        except (requests.RequestException, ValueError, KeyError, IndexError) as e:
            raise RuntimeError(f"无法从 Gradio API 服务器获取共享服务器地址: {e}") from e

        self._tunnel = gradio_tunneling.Tunnel(
            remote_host=remote_host,
            remote_port=remote_port,
            local_host="127.0.0.1",
            local_port=self.port,
            share_token=secrets.token_urlsafe(32),
        )
        try:
            # 首次使用时会下载 frpc, 之后等待 frpc 输出公网地址
            self._url = self._tunnel.start_tunnel()
        except Exception as e:
            self.stop()
            raise RuntimeError(f"启动 Gradio 内网穿透失败: {e}") from e
        return self._url

    def stop(
        self,
    ) -> None:
        """停止 Gradio 内网穿透"""
        if self._tunnel is None:
            return
        try:
            self._tunnel.kill()
        except OSError as e:
            logger.warning("停止 Gradio 内网穿透时出现错误: %s", e)
        self._tunnel = None
        self._url = None

    @property
    def url(
        self,
    ) -> str | None:
        """公网访问地址, 未启动时为 None"""
        return self._url
