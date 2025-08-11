#!/bin/bash
# PVE签到工具安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
INSTALL_DIR="/opt/checkin"
PYTHON_CMD="python3"

echo -e "${GREEN}PVE自动签到工具安装脚本${NC}"
echo "=================================="

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}错误: 请以root用户运行此脚本${NC}"
   exit 1
fi

# 检查Python环境
echo "检查Python环境..."
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3，请先安装${NC}"
    exit 1
fi

python3_version=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}Python版本: $python3_version${NC}"

# 检查pip
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo -e "${YELLOW}安装pip...${NC}"
    apt-get update && apt-get install -y python3-pip
fi

# 安装requests库
echo "检查Python依赖..."
if ! $PYTHON_CMD -c "import requests" &> /dev/null; then
    echo -e "${YELLOW}安装requests库...${NC}"
    $PYTHON_CMD -m pip install requests
fi

# 创建安装目录
echo "创建安装目录..."
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

# 检查文件是否存在
if [[ ! -f "pve_checkin_cron.py" ]]; then
    echo -e "${RED}错误: 未找到pve_checkin_cron.py文件${NC}"
    echo "请将以下文件上传到 $INSTALL_DIR 目录："
    echo "- pve_checkin_cron.py"
    echo "- pve_checkin_config.json"
    exit 1
fi

# 设置文件权限
echo "设置文件权限..."
chmod +x pve_checkin_cron.py
chmod 600 pve_checkin_config.json
chown root:root *

# 测试运行
echo "测试工具运行..."
if $PYTHON_CMD pve_checkin_cron.py --test; then
    echo -e "${GREEN}测试运行成功!${NC}"
else
    echo -e "${RED}测试运行失败，请检查配置${NC}"
    exit 1
fi

# 配置crontab
echo -e "${YELLOW}配置定时任务...${NC}"
echo "请选择签到时间:"
echo "1) 每天 09:00 (推荐)"
echo "2) 每天 08:00"
echo "3) 每天 10:00"
echo "4) 自定义时间"
echo "5) 跳过crontab配置"

read -p "请选择 [1-5]: " choice

case $choice in
    1)
        CRON_TIME="0 9 * * *"
        ;;
    2)
        CRON_TIME="0 8 * * *"
        ;;
    3)
        CRON_TIME="0 10 * * *"
        ;;
    4)
        read -p "请输入cron时间格式 (如: 0 9 * * *): " CRON_TIME
        ;;
    5)
        echo -e "${YELLOW}跳过crontab配置${NC}"
        CRON_TIME=""
        ;;
    *)
        echo -e "${YELLOW}无效选择，使用默认时间 09:00${NC}"
        CRON_TIME="0 9 * * *"
        ;;
esac

if [[ -n "$CRON_TIME" ]]; then
    # 检查是否已存在相同的cron任务
    CRON_CMD="$PYTHON_CMD $INSTALL_DIR/pve_checkin_cron.py >/dev/null 2>&1"
    CRON_ENTRY="$CRON_TIME $CRON_CMD"
    
    # 获取现有crontab
    TEMP_CRON=$(mktemp)
    crontab -l > "$TEMP_CRON" 2>/dev/null || true
    
    # 检查是否已存在
    if grep -q "pve_checkin_cron.py" "$TEMP_CRON"; then
        echo -e "${YELLOW}检测到现有的签到任务，正在更新...${NC}"
        # 删除现有的签到任务
        sed -i '/pve_checkin_cron.py/d' "$TEMP_CRON"
    fi
    
    # 添加新的任务
    echo "$CRON_ENTRY" >> "$TEMP_CRON"
    
    # 安装crontab
    crontab "$TEMP_CRON"
    rm "$TEMP_CRON"
    
    echo -e "${GREEN}Crontab配置完成!${NC}"
    echo "定时任务: $CRON_TIME"
    echo "命令: $CRON_CMD"
fi

echo
echo -e "${GREEN}安装完成!${NC}"
echo "=================================="
echo "安装目录: $INSTALL_DIR"
echo "主程序: pve_checkin_cron.py" 
echo "配置文件: pve_checkin_config.json"
echo "日志文件: pve_checkin_YYYYMM.log"
echo
echo "常用命令:"
echo "# 手工测试运行"
echo "$PYTHON_CMD $INSTALL_DIR/pve_checkin_cron.py --test"
echo
echo "# 查看日志"
echo "tail -f $INSTALL_DIR/pve_checkin_*.log"
echo
echo "# 查看crontab配置"
echo "crontab -l"
echo
echo "# 编辑配置文件"
echo "nano $INSTALL_DIR/pve_checkin_config.json"
echo
echo -e "${YELLOW}注意: 请编辑配置文件中的邮件设置！${NC}"
echo -e "${YELLOW}Gmail需要使用应用专用密码，详见部署指南${NC}"