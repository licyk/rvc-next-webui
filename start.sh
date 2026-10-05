#!/bin/bash

if ! python3 -V &> /dev/null; then
    echo "未找到 Python, 终止运行"
    read -p "按 Enter 键继续..."
    exit 1
fi

if ! python3 -c "import venv, ensurepip" &> /dev/null; then
    echo "未找到 Python venv 模块, 终止运行 (Debian / Ubuntu 上需要安装 python3-venv)"
    read -p "按 Enter 键继续..."
    exit 1
fi

cd "$(cd "$(dirname "$0")" ; pwd)"

if [[ ! -f "./venv/bin/activate" ]]; then
    echo "创建虚拟环境中..."
    if ! python3 -m venv venv; then
        echo "创建虚拟环境失败, 终止运行"
        read -p "按 Enter 键继续..."
        exit 1
    fi
fi

source ./venv/bin/activate

python launch.py "$@"
status=$?

read -p "按 Enter 键继续..."
exit $status
