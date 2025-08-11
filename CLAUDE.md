# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个专为Proxmox VE (PVE)环境设计的自动签到工具，用于mirror.o3pro.pro网站的自动签到。该工具具备Token自动刷新、SMTP邮件通知和状态持久化等功能。

## 核心架构

### 主要组件
- `pve_checkin_cron.py` - 主程序，包含完整的签到逻辑
- `pve_checkin_config.json` - 配置文件，存储用户凭证和邮件设置
- `pve_checkin_status.json` - 状态文件（运行时生成），避免重复签到
- `pve_checkin_YYYYMM.log` - 月度日志文件（自动生成）

### 核心类结构
- `PVECheckinCron` - 主要的签到管理类，处理：
  - 配置加载和管理
  - Token验证和自动刷新
  - 签到操作执行
  - SMTP邮件通知
  - 日志管理和状态持久化

### API交互端点
- 基础URL: `https://mirror.o3pro.pro`
- 登录: `/api/auth/login` (POST)
- 用户验证: `/api/auth/user` (GET)
- 签到: `/api/checkin` (POST)
- 积分查询: `/api/credits/balance` (GET)

## 常用开发和测试命令

### 本地运行
```bash
# 测试模式运行 - 显示详细输出和日志
python3 pve_checkin_cron.py --test

# 正常模式运行 - 适用于crontab
python3 pve_checkin_cron.py

# 指定配置文件路径
python3 pve_checkin_cron.py --config=/opt/checkin/pve_checkin_config.json

# 测试邮件发送功能
python3 pve_checkin_cron.py --test-email

# 组合使用
python3 pve_checkin_cron.py --test --config=/path/to/config.json
```

### GitHub Actions运行
```bash
# GitHub Actions专用版本测试
python3 github_actions_checkin.py --test

# GitHub Actions专用版本正常运行
python3 github_actions_checkin.py
```

## 部署和运行

### GitHub Actions部署（推荐）
```bash
# 1. Fork仓库到个人GitHub账户
# 2. 配置Repository Secrets（详见GITHUB_ACTIONS_SETUP.md）：
#    - LOGIN_EMAIL: 登录邮箱
#    - LOGIN_PASSWORD: 登录密码  
#    - AUTH_TOKEN: JWT令牌
#    - 邮件相关配置（可选）
# 3. 工作流将每天北京时间9点自动执行

# 手动触发工作流
# 在GitHub仓库Actions页面点击"Run workflow"
```

### PVE环境部署
```bash
# 创建目录并设置权限
mkdir -p /opt/checkin
chmod +x /opt/checkin/pve_checkin_cron.py
chmod 600 /opt/checkin/pve_checkin_config.json

# 安装Python依赖
pip3 install requests

# 配置crontab定时任务
0 9 * * * /usr/bin/python3 /opt/checkin/pve_checkin_cron.py >/dev/null 2>&1
```

### 使用自动安装脚本
```bash
# 运行安装脚本（需要root权限）
chmod +x install_pve_checkin.sh
sudo ./install_pve_checkin.sh
```

## 配置要点

### 关键配置结构
```json
{
  "login": {
    "email": "用户邮箱",
    "password": "用户密码"
  },
  "auth_token": "JWT令牌（自动更新）",
  "email_alerts": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "发件邮箱",
    "smtp_password": "应用专用密码",
    "on_failure": true,
    "on_success": false,
    "on_token_refresh": true
  }
}
```

### Gmail邮件配置注意事项
- 必须使用应用专用密码，不能使用账户密码
- 需要开启两步验证
- 支持SSL(465)和STARTTLS(587)两种连接方式

## 日志和调试

### 日志文件位置
- 日志文件：`pve_checkin_YYYYMM.log`（按月轮转）
- 状态文件：`pve_checkin_status.json`
- 自动清理：保留30天日志（可配置）

### 调试方法
```bash
# 查看实时日志
tail -f /opt/checkin/pve_checkin_*.log

# 检查配置文件语法
python3 -m json.tool pve_checkin_config.json

# 测试网络连接
curl -I https://mirror.o3pro.pro/
```

## 关键功能特性

1. **智能Token管理** - 自动检测Token失效并重新登录
2. **防重复签到** - 基于状态文件的去重机制
3. **多级邮件通知** - 失败/成功/Token刷新三种通知类型
4. **错误重试机制** - 可配置的重试次数和延迟
5. **日志轮转** - 自动清理过期日志文件
6. **测试模式** - 便于开发和调试的详细输出模式

## 错误处理

- HTTP 401错误会触发自动Token刷新
- 网络错误有重试机制
- 配置文件错误会使用默认配置
- 所有异常都会记录详细日志并发送邮件通知

## 安全考虑

- 配置文件权限设置为600（仅owner可读写）
- 支持应用专用密码，避免明文密码
- 敏感信息不会输出到日志中
- crontab静默运行，避免输出敏感信息