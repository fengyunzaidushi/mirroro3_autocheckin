# GitHub Actions 部署指南

## 概述

本项目已配置GitHub Actions工作流，可以在GitHub上自动执行每日签到任务。

## 配置步骤

### 1. 设置Repository Secrets

在GitHub仓库中设置以下Secrets：

**必需的Secrets：**
- `LOGIN_EMAIL` - 登录mirror.o3pro.pro的邮箱
- `LOGIN_PASSWORD` - 登录密码
- `AUTH_TOKEN` - JWT认证令牌（首次运行可留空，程序会自动获取）

**邮件通知相关Secrets（可选）：**
- `EMAIL_ENABLED` - 是否启用邮件通知（true/false）
- `SMTP_SERVER` - SMTP服务器地址（如：smtp.163.com）
- `SMTP_PORT` - SMTP端口（如：465）
- `SMTP_USER` - SMTP用户名
- `SMTP_PASSWORD` - SMTP密码/授权码
- `FROM_EMAIL` - 发件人邮箱
- `TO_EMAIL` - 收件人邮箱

### 2. 如何设置Secrets

1. 进入GitHub仓库页面
2. 点击 `Settings` 选项卡
3. 在左侧菜单选择 `Secrets and variables` > `Actions`
4. 点击 `New repository secret`
5. 输入Secret名称和值
6. 点击 `Add secret` 保存

### 3. 163邮箱配置示例

对于163邮箱，设置以下Secrets：
```
EMAIL_ENABLED=true
SMTP_SERVER=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASSWORD=your_163_authorization_code
FROM_EMAIL=your_email@163.com
TO_EMAIL=your_email@163.com
```

## 工作流功能

### 自动执行
- 每天北京时间上午9点自动执行签到
- 使用cron表达式：`0 1 * * *`（UTC时间）

### 手动执行
- 在Actions页面可以手动触发工作流
- 支持测试模式，显示详细日志输出

### 日志管理
- 自动上传执行日志为Artifacts
- 日志保留30天
- 可在Actions页面下载查看

## 安全特性

1. **敏感信息保护** - 所有登录信息存储在GitHub Secrets中
2. **配置文件安全** - `.gitignore`确保本地配置文件不被提交
3. **配置文件清理** - 运行完成后自动删除临时配置文件
4. **Token自动刷新** - JWT令牌失效时自动重新登录
5. **错误处理** - 包含完整的错误处理和重试机制

## 本地开发注意事项

1. **配置文件模板** - 使用 `pve_checkin_config.json.example` 作为模板
2. **创建本地配置** - 复制模板为 `pve_checkin_config.json` 并填入真实配置
3. **Git安全** - `.gitignore` 已配置忽略包含敏感信息的配置文件
4. **不要提交敏感信息** - 确保密码、Token等不会被意外提交到仓库

## 使用说明

### 初次部署
1. Fork或克隆此仓库到你的GitHub账户
2. 按照上述步骤配置Secrets
3. 工作流将自动在每天上午9点执行

### 手动测试
1. 进入GitHub仓库的Actions页面
2. 选择"Mirror O3 Pro Auto Checkin"工作流
3. 点击"Run workflow"
4. 选择是否以测试模式运行
5. 点击"Run workflow"开始执行

### 查看结果
1. 在Actions页面查看工作流执行状态
2. 点击具体的运行实例查看详细日志
3. 下载Artifacts中的日志文件查看完整记录
4. 如果配置了邮件通知，会收到相关邮件

## 故障排除

### 常见问题
1. **签到失败** - 检查LOGIN_EMAIL和LOGIN_PASSWORD是否正确
2. **Token失效** - 工作流会自动处理，重新登录获取新token
3. **邮件发送失败** - 检查SMTP相关配置是否正确

### 调试方法
1. 使用手动触发的测试模式查看详细日志
2. 检查Secrets配置是否完整
3. 查看Actions执行日志中的错误信息

## 注意事项

1. GitHub Actions有使用配额限制，但对于简单的签到任务通常足够
2. 建议定期检查工作流执行状态
3. 如需修改执行时间，编辑`.github/workflows/auto-checkin.yml`中的cron表达式
4. 保护好GitHub仓库的访问权限，避免泄露敏感信息