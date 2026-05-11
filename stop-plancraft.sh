#!/bin/bash

PID_FILE="/Users/joyfor/Documents/trae_projects/21/.ssuma_pids"

if [ -f "$PID_FILE" ]; then
    echo "🛑 正在停止 PlanCraft 服务..."
    kill $(cat "$PID_FILE") 2>/dev/null
    rm "$PID_FILE"
    echo "✅ 服务已停止"
else
    echo "ℹ️ 未找到运行中的服务"
fi
