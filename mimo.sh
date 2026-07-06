#!/bin/bash
# Mimo AI Chatbot 啟動腳本

# 強制不緩衝標準輸出，確保狀態機日誌即時顯示
export PYTHONUNBUFFERED=1

# 取得腳本所在的目錄路徑
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 檢查虛擬環境並執行
if [ -f "./bin/activate" ]; then
    echo "⚙️ 正在啟用 Mimo 本地虛擬環境並啟動系統..."
    ./bin/python -u main.py "$@"
else
    echo "⚠️ 找不到本地虛擬環境，嘗試使用系統 Python 啟動..."
    python3 -u main.py "$@"
fi
