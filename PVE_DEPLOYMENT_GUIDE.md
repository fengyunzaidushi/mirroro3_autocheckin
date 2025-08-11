# PVE Crontab 自动签到工具部署指南

## 功能特性

1. **Token自动刷新**: 当JWT token失效时自动重新登录获取新token
2. **SMTP邮件预警**: 支持签到失败、成功、token刷新等场景的邮件通知
3. **PVE环境优化**: 适配PVE环境的crontab定时任务
4. **错误重试机制**: 支持失败重试和状态持久化
5. **日志管理**: 自动清理过期日志文件
6. **测试模式**: 提供手工测试模式验证配置

## 文件说明

- `pve_checkin_cron.py` - 主程序文件
- `pve_checkin_config.json` - 配置文件
- `pve_checkin_status.json` - 运行状态记录（自动生成）
- `pve_checkin_YYYYMM.log` - 月度日志文件（自动生成）

## 安装部署

### 1. 上传文件到PVE

将以下文件上传到PVE系统的目标目录（建议 `/opt/checkin/`）：
```bash
/opt/checkin/
├── pve_checkin_cron.py
└── pve_checkin_config.json
```

### 2. 设置文件权限

```bash
sudo chmod +x /opt/checkin/pve_checkin_cron.py
sudo chown root:root /opt/checkin/*
```

### 3. 安装Python依赖

```bash
# 确保安装了requests库
pip3 install requests
```

### 4. 配置邮件参数

编辑 `/opt/checkin/pve_checkin_config.json`，修改邮件配置：

```json
{
  "email_alerts": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your_email@gmail.com",
    "smtp_password": "your_app_password",  // Gmail需要使用应用专用密码
    "from_email": "your_email@gmail.com",
    "to_email": "your_notify_email@gmail.com",
    "on_failure": true,      // 失败时发邮件
    "on_success": false,     // 成功时不发邮件
    "on_token_refresh": true // Token刷新时发邮件
  }
}
```

**Gmail应用专用密码设置**：
1. 登录Gmail -> 设置 -> 安全性
2. 开启两步验证
3. 生成应用专用密码
4. 将应用专用密码填入smtp_password

### 5. 测试运行

在PVE上手工执行测试：

```bash
# 测试模式运行（会输出详细信息）
python3 /opt/checkin/pve_checkin_cron.py --test

# 正常模式运行
python3 /opt/checkin/pve_checkin_cron.py
```

测试成功后会看到类似输出：
```
PVE签到工具测试模式
配置文件: /opt/checkin/pve_checkin_config.json
状态文件: /opt/checkin/pve_checkin_status.json
日志文件: /opt/checkin/pve_checkin_202508.log
--------------------------------------------------
签到结果: 成功
日志已记录到: /opt/checkin/pve_checkin_202508.log
```

### 6. 配置Crontab

```bash
# 编辑root用户的crontab
sudo crontab -e

# 添加定时任务（每天早上9点执行）
0 9 * * * /usr/bin/python3 /opt/checkin/pve_checkin_cron.py >/dev/null 2>&1

# 或者指定配置文件路径
0 9 * * * /usr/bin/python3 /opt/checkin/pve_checkin_cron.py --config=/opt/checkin/pve_checkin_config.json >/dev/null 2>&1
```

### 7. 验证Crontab配置

```bash
# 查看当前crontab配置
sudo crontab -l

# 查看cron服务状态
sudo systemctl status cron

# 查看cron日志
sudo tail -f /var/log/syslog | grep CRON
```

## 配置参数说明

### 基础配置
- `login.email` - 登录邮箱
- `login.password` - 登录密码
- `auth_token` - 当前有效的JWT token（会自动更新）
- `max_retries` - 最大重试次数（默认3次）
- `retry_delay` - 重试延迟秒数（默认300秒）

### 邮件配置
- `email_alerts.enabled` - 是否启用邮件通知
- `email_alerts.smtp_server` - SMTP服务器地址
- `email_alerts.smtp_port` - SMTP端口（587/465）
- `email_alerts.smtp_user` - SMTP用户名
- `email_alerts.smtp_password` - SMTP密码/应用专用密码
- `email_alerts.from_email` - 发件人邮箱
- `email_alerts.to_email` - 收件人邮箱
- `email_alerts.on_failure` - 失败时是否发邮件
- `email_alerts.on_success` - 成功时是否发邮件
- `email_alerts.on_token_refresh` - Token刷新时是否发邮件

### 日志配置
- `logging.level` - 日志级别（DEBUG/INFO/WARNING/ERROR）
- `logging.max_log_days` - 日志保留天数（默认30天）

## 命令行参数

```bash
# 正常运行
python3 pve_checkin_cron.py

# 测试模式（显示详细输出）
python3 pve_checkin_cron.py --test

# 指定配置文件路径
python3 pve_checkin_cron.py --config=/path/to/config.json

# 组合使用
python3 pve_checkin_cron.py --test --config=/opt/checkin/pve_checkin_config.json
```

## 故障排查

### 1. 查看日志
```bash
# 查看最新日志
tail -f /opt/checkin/pve_checkin_*.log

# 查看特定时间段日志
grep "2025-08-07" /opt/checkin/pve_checkin_202508.log
```

### 2. 常见问题

**Token失效**
- 程序会自动重新登录获取新token
- 如果登录失败，检查用户名密码是否正确
- 检查网络连接是否正常

**邮件发送失败**
- 检查SMTP配置是否正确
- Gmail需要使用应用专用密码，不能使用账户密码
- 检查防火墙是否阻止SMTP连接

**签到失败**
- 检查网络连接
- 查看日志中的具体错误信息
- 手工运行测试模式进行调试

**权限问题**
```bash
# 检查文件权限
ls -la /opt/checkin/

# 修正权限
sudo chown root:root /opt/checkin/*
sudo chmod +x /opt/checkin/pve_checkin_cron.py
sudo chmod 600 /opt/checkin/pve_checkin_config.json
```

### 3. 手工调试

```bash
# 详细调试模式
python3 /opt/checkin/pve_checkin_cron.py --test

# 检查配置文件语法
python3 -m json.tool /opt/checkin/pve_checkin_config.json

# 测试网络连接
curl -I https://mirror.o3pro.pro/
```

## 高级配置

### 多时间段签到
如果需要一天多次尝试签到：
```bash
# 每天9点和21点各尝试一次
0 9 * * * /usr/bin/python3 /opt/checkin/pve_checkin_cron.py >/dev/null 2>&1
0 21 * * * /usr/bin/python3 /opt/checkin/pve_checkin_cron.py >/dev/null 2>&1
```

### 自定义邮件服务器
支持其他邮件提供商：
```json
{
  "email_alerts": {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "smtp_user": "your_qq@qq.com",
    "smtp_password": "your_auth_code"
  }
}
```

### 日志轮转
可配合logrotate进行日志轮转：
```bash
# 创建logrotate配置
sudo vim /etc/logrotate.d/pve-checkin

# 内容如下：
/opt/checkin/pve_checkin_*.log {
    monthly
    rotate 12
    compress
    delaycompress
    create 644 root root
}
```

## 安全建议

1. **配置文件权限**: 设置为600，避免密码泄露
2. **定期更新密码**: 定期更新登录密码和邮件密码
3. **日志监控**: 定期检查日志，发现异常及时处理
4. **备份配置**: 定期备份配置文件
5. **网络安全**: 确保PVE系统的网络安全配置

## 更新维护

当需要更新工具时：
1. 备份当前配置和状态文件
2. 替换主程序文件
3. 比较配置文件差异，必要时更新配置
4. 运行测试模式验证功能正常