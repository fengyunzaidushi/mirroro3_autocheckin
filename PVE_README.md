# PVE自动签到工具快速部署包

## 文件清单

- `pve_checkin_cron.py` - 主程序文件
- `pve_checkin_config.json` - 配置文件
- `install_pve_checkin.sh` - 自动安装脚本
- `PVE_DEPLOYMENT_GUIDE.md` - 详细部署指南
- `README.md` - 本文件

## 快速开始

### 1. 上传文件到PVE
```bash
# 创建目录并上传文件
mkdir -p /opt/checkin
cd /opt/checkin
# 上传以下文件到此目录：
# - pve_checkin_cron.py
# - pve_checkin_config.json
# - install_pve_checkin.sh (可选)
```

### 2. 设置权限并测试
```bash
chmod +x /opt/checkin/pve_checkin_cron.py
chmod +x /opt/checkin/install_pve_checkin.sh
chmod 600 /opt/checkin/pve_checkin_config.json

# 测试运行
python3 /opt/checkin/pve_checkin_cron.py --test
```

### 3. 配置邮件通知
编辑 `/opt/checkin/pve_checkin_config.json`，更新邮件配置：
```json
{
  "email_alerts": {
    "enabled": true,
    "smtp_user": "your_email@gmail.com",
    "smtp_password": "your_app_password",
    "from_email": "your_email@gmail.com",
    "to_email": "your_notify_email@gmail.com"
  }
}
```

### 4. 配置定时任务
```bash
# 编辑crontab
crontab -e

# 添加定时任务（每天早上9点）
0 9 * * * /usr/bin/python3 /opt/checkin/pve_checkin_cron.py >/dev/null 2>&1
```

### 5. 验证部署
```bash
# 查看日志
tail -f /opt/checkin/pve_checkin_*.log

# 查看crontab
crontab -l
```

## 主要功能

1. ✅ **Token自动刷新** - token失效时自动重新登录
2. ✅ **SMTP邮件预警** - 支持失败、成功、token刷新通知
3. ✅ **状态持久化** - 避免重复签到和失败重试
4. ✅ **日志管理** - 自动清理过期日志
5. ✅ **测试模式** - 方便手工验证配置

## 故障排查

**签到失败**:
```bash
python3 /opt/checkin/pve_checkin_cron.py --test
tail -f /opt/checkin/pve_checkin_*.log
```

**邮件不发送**:
- 检查Gmail应用专用密码设置
- 确认SMTP配置正确

**权限问题**:
```bash
sudo chown root:root /opt/checkin/*
sudo chmod +x /opt/checkin/pve_checkin_cron.py
sudo chmod 600 /opt/checkin/pve_checkin_config.json
```

详细说明请查看 `PVE_DEPLOYMENT_GUIDE.md`