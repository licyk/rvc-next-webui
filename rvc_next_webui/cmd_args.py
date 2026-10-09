"""命令行参数解析"""

import argparse
from pathlib import Path

from rvc_next_webui.config import (
    DATA_PATH,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    TORCH_BACKEND_CHOICES,
)


def get_args_parser() -> argparse.ArgumentParser:
    """获取命令行参数解析器

    Returns:
        argparse.ArgumentParser:
            命令行参数解析器
    """
    parser = argparse.ArgumentParser(description="RVC Next WebUI 启动器")

    server = parser.add_argument_group("服务器")
    server.add_argument(
        "--data-dir", type=Path, default=DATA_PATH, help=f"RVC Next 数据目录, 保存设置, 数据库, 模型和输出 (默认为 {DATA_PATH})"
    )
    server.add_argument("--config-dir", type=Path, default=None, help="保存 settings.toml 的目录 (默认为数据目录)")
    server.add_argument(
        "--host",
        type=str,
        default=DEFAULT_SERVER_HOST,
        help=f"监听地址 (默认为 {DEFAULT_SERVER_HOST}), 非本机地址需要同时设置 --access-token",
    )
    server.add_argument(
        "--port",
        type=int,
        default=DEFAULT_SERVER_PORT,
        help=f"监听端口 (默认为 {DEFAULT_SERVER_PORT}, 0 为任意空闲端口), 端口被占用时尝试下一个端口",
    )
    server.add_argument("--strict-port", action="store_true", help="端口被占用时直接退出, 不尝试下一个端口")
    server.add_argument("--access-token", type=str, default=None, help="访问令牌, 监听非本机地址时必须设置")
    server.add_argument("--api-prefix", type=str, default=None, help="将 API 和 WebUI 挂载到指定路径下, 如 /voice")
    server.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    server.add_argument(
        "--share",
        action="store_true",
        help="使用 Gradio 内网穿透生成公网访问地址 (有效期 72 小时), 未设置 --access-token 时自动生成访问令牌",
    )

    proxy = parser.add_argument_group("代理")
    proxy.add_argument("--proxy", type=str, default=None, help="手动指定代理地址, 如 http://127.0.0.1:7890 (默认自动读取系统代理)")
    proxy.add_argument("--disable-proxy", action="store_true", help="禁用自动设置代理")

    env = parser.add_argument_group("运行环境")
    env.add_argument("--skip-check", action="store_true", help="跳过运行环境的依赖检查")
    env.add_argument(
        "--torch-backend", choices=TORCH_BACKEND_CHOICES, default="auto", help="安装 PyTorch 时使用的类型 (默认为 auto, 根据显卡自动选择)"
    )
    env.add_argument("--reinstall-torch", action="store_true", help="重新安装 PyTorch, 可与 --torch-backend 一起使用")
    env.add_argument("--index-url", type=str, default=None, help="安装项目依赖时使用的 PyPI 镜像地址 (不影响 PyTorch 的安装)")

    parser.add_argument("--debug", action="store_true", help="启用 Debug 日志")
    parser.add_argument("--version", action="store_true", help="显示版本信息")
    return parser
