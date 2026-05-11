#!/bin/bash

# PlanCraft 一键启动脚本

ROOT_DIR="/Users/joyfor/Documents/trae_projects/21"
BACKEND_DIR="$ROOT_DIR/Ssuma/backend"
FRONTEND_DIR="$ROOT_DIR/Ssuma/frontend"
PID_FILE="$ROOT_DIR/.ssuma_pids"
LOG_DIR="$ROOT_DIR/logs"

mkdir -p "$LOG_DIR"

echo "🚀 正在启动 PlanCraft..."

# 清理旧进程
if [ -f "$PID_FILE" ]; then
    echo "⚠️ 检测到旧进程，正在清理..."
    kill $(cat "$PID_FILE") 2>/dev/null
    rm "$PID_FILE"
fi

# 1. 启动后端
echo "🔧 启动后端服务 (Port 8000)..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/python3 -m pip install -r requirements.txt -q
nohup ./venv/bin/python3 -m uvicorn main:app --reload --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
echo $! >> "$PID_FILE"

# 等待后端启动
sleep 3

# 2. 启动前端
echo "🎨 启动前端服务 (Port 3000)..."
cd "$FRONTEND_DIR"
npm install --silent
nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
echo $! >> "$PID_FILE"

# 等待前端启动
sleep 5

echo "✅ PlanCraft 启动完成！"
echo "---------------------------------------"
echo "后端日志: tail -f $LOG_DIR/backend.log"
echo "前端日志: tail -f $LOG_DIR/frontend.log"
echo "访问地址: http://localhost:3000"
echo "---------------------------------------"
echo "💡 服务已在后台运行，可直接访问浏览器测试。"
echo "运行 ./stop-plancraft.sh 可停止服务。"

open http://localhost:3000

