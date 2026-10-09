"""Gradio 内网穿透

使用 gradio-tunneling 库通过 Gradio 的共享服务器生成公网访问地址 (https://xxx.gradio.live), 有效期为 72 小时.

隧道转发的请求会保留公网地址的 Host 请求头, 需要通过 ``RvcNextServer.allow_host()`` 允许该地址.
gradio-tunneling 由依赖检查安装, 本模块需要在依赖检查完成后才能导入.
"""

import secrets

import requests
from gradio_tunneling.main import GRADIO_API_SERVER, Tunnel

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

GRADIO_API_TIMEOUT = 10
"""请求 Gradio API 服务器的超时时间 (秒)"""


class GradioTunnel:
    """Gradio 内网穿透"""

    def __init__(
        self,
        port: int,
    ) -> None:
        """初始化 Gradio 内网穿透

        Args:
            port (int):
                要进行端口映射的本地端口
        """
        self.port = port
        self._tunnel: Tunnel | None = None
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
        try:
            response = requests.get(GRADIO_API_SERVER, timeout=GRADIO_API_TIMEOUT)
            response.raise_for_status()
            payload = response.json()[0]
            remote_host, remote_port = payload["host"], int(payload["port"])
        except (requests.RequestException, ValueError, KeyError, IndexError) as e:
            raise RuntimeError(f"无法从 Gradio API 服务器获取共享服务器地址: {e}") from e

        self._tunnel = Tunnel(
            remote_host=remote_host,
            remote_port=remote_port,
            local_host="127.0.0.1",
            local_port=self.port,
            share_token=secrets.token_urlsafe(32),
        )
        try:
            # 等待 frpc 输出公网地址
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
