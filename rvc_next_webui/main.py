"""主启动文件"""

import argparse
import logging
import os
import signal
import sys
from types import FrameType

from rvc_next_webui.cmd_args import get_args_parser
from rvc_next_webui.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from rvc_next_webui.env_check import check_environment
from rvc_next_webui.logger import get_logger
from rvc_next_webui.version import VERSION

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def _raise_keyboard_interrupt(
    _signum: int,
    _frame: FrameType | None,
) -> None:
    """将收到的信号转为 KeyboardInterrupt

    Args:
        _signum (int):
            信号编号
        _frame (FrameType | None):
            收到信号时的栈帧

    Raises:
        KeyboardInterrupt:
            总是抛出
    """
    raise KeyboardInterrupt


def launch_rvc_next(
    args: argparse.Namespace,
) -> None:
    """以嵌入模式启动 RVC Next WebUI, 阻塞直到服务器停止

    Args:
        args (argparse.Namespace):
            命令行参数
    """
    data_dir = args.data_dir.expanduser().resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    # 与 `rvc-next webui` 一致, 让子进程和命令行使用同一个数据目录
    os.environ["RVC_NEXT_DATA_DIR"] = data_dir.as_posix()
    config_dir = None
    if args.config_dir is not None:
        config_dir = args.config_dir.expanduser().resolve()
        os.environ["RVC_NEXT_CONFIG_DIR"] = config_dir.as_posix()

    # rvc-next 需要在依赖检查完成后才能导入
    from rvc_next import RvcNextServer
    from rvc_next.core.net.ports import PortUnavailableError
    from rvc_next.logger import setup_logging
    from rvc_next.version import VERSION as RVC_NEXT_VERSION

    setup_logging(logging.DEBUG if args.debug else None)
    logger.info("RVC Next 版本: %s, 数据目录: %s", RVC_NEXT_VERSION, data_dir)

    server = RvcNextServer(
        data_dir=data_dir,
        config_dir=config_dir,
        host=args.host,
        port=args.port,
        strict_port=args.strict_port,
        api_prefix=args.api_prefix,
        open_browser=not args.no_browser,
        access_token=args.access_token,
        log_level="debug" if args.debug else "warning",
    )
    try:
        server.start()
    except PortUnavailableError as e:
        logger.error("RVC Next WebUI 启动失败: %s", e)
        sys.exit(1)

    logger.info("RVC Next WebUI 已启动, 访问地址: %s", server.url)
    logger.info("按 Ctrl+C 停止 RVC Next WebUI")
    # 嵌入模式下 uvicorn 运行在子线程中, 不会处理 SIGTERM, 转为 Ctrl+C 使服务器正常停止
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    # run() 在已启动时不会重复启动, 只负责阻塞并在 Ctrl+C 后停止服务器
    server.run()
    logger.info("RVC Next WebUI 已停止")


def main() -> None:
    """主函数"""
    args = get_args_parser().parse_args()
    if args.version:
        print(f"RVC Next WebUI {VERSION}")
        return

    if args.debug:
        logging.getLogger(LOGGER_NAME).setLevel(logging.DEBUG)

    logger.info("初始化 RVC Next WebUI")
    if args.skip_check:
        logger.info("跳过运行环境检查")
    else:
        try:
            check_environment(
                backend=args.torch_backend,
                reinstall_torch=args.reinstall_torch,
                index_url=args.index_url,
            )
        except (RuntimeError, FileNotFoundError) as e:
            logger.error("运行环境检查失败: %s", e)
            sys.exit(1)

    launch_rvc_next(args)
