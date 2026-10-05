"""启动文件"""

import sys

if sys.version_info < (3, 10):
    print(f"RVC Next WebUI 需要 Python 3.10 及以上版本, 当前版本为 {sys.version.split()[0]}")
    sys.exit(1)

from rvc_next_webui import main

if __name__ == "__main__":
    main()
