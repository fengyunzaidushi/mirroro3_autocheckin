#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PVE Crontab 自动签到工具 - mirror.o3pro.pro
适用于PVE环境的crontab定时任务，支持token失效重登录和SMTP邮件预警
"""

import requests
import json
import logging
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

class PVECheckinCron:
    def __init__(self, config_path=None):
        # 确定配置文件路径 - 优先使用传入路径，然后是脚本目录，最后是当前目录
        if config_path:
            self.config_file = Path(config_path)
        else:
            script_dir = Path(__file__).parent.absolute()
            self.config_file = script_dir / "pve_checkin_config.json"
            
        self.status_file = self.config_file.parent / "pve_checkin_status.json"
        self.log_file = self.config_file.parent / f"pve_checkin_{datetime.now().strftime('%Y%m')}.log"
        
        self.base_url = "https://mirror.o3pro.pro"
        
        # 加载配置
        self.load_config()
        
        # 设置日志
        self.setup_logging()
        
        # 设置基础请求头
        self.base_headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://mirror.o3pro.pro',
            'Referer': 'https://mirror.o3pro.pro/',
            'Content-Type': 'application/json'
        }
        
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "login": {
                "email": "your_mirroro3_login_email",
                "password": "your_mirroro3_login_password"
            },
            "auth_token": "your_mirroro3_auth_token",
            "user_info": {
                "id": 0,
                "username": "your_username",
                "email": "your_email@example.com"
            },
            "max_retries": 3,
            "retry_delay": 300,
            "email_alerts": {
                "enabled": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_user": "your_email@gmail.com",
                "smtp_password": "your_app_password",
                "from_email": "your_email@gmail.com",
                "to_email": "your_notification_email@example.com",
                "on_failure": True,
                "on_success": False,
                "on_token_refresh": True
            },
            "logging": {
                "level": "INFO",
                "max_log_days": 30
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 递归合并配置，保留默认值
                    self.config = self._merge_config(default_config, loaded_config)
            except Exception as e:
                print(f"配置文件读取失败: {e}")
                self.config = default_config
        else:
            self.config = default_config
            
        # 自动保存配置（确保有完整配置）
        self.save_config()
            
    def _merge_config(self, default, loaded):
        """递归合并配置"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
            
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
            
    def setup_logging(self):
        """配置日志系统 - PVE环境优化"""
        log_level = getattr(logging, self.config['logging']['level'], logging.INFO)
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # 清理旧日志文件
        self._cleanup_old_logs()
        
        # 配置日志处理器
        handlers = [
            logging.FileHandler(self.log_file, encoding='utf-8')
        ]
        
        # 如果是测试模式或交互式环境，也输出到控制台
        if '--test' in sys.argv or os.isatty(sys.stdout.fileno()):
            handlers.append(logging.StreamHandler(sys.stdout))
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers,
            force=True
        )
        
        self.logger = logging.getLogger(__name__)
        
    def _cleanup_old_logs(self):
        """清理过期日志文件"""
        try:
            max_days = self.config['logging']['max_log_days']
            cutoff_date = datetime.now() - timedelta(days=max_days)
            
            log_pattern = "pve_checkin_*.log"
            for log_file in self.config_file.parent.glob(log_pattern):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    
        except Exception as e:
            pass  # 静默处理清理错误
            
    def get_auth_headers(self):
        """获取带认证的请求头"""
        headers = self.base_headers.copy()
        headers['Authorization'] = f'Bearer {self.config["auth_token"]}'
        return headers
        
    def login_and_get_token(self):
        """登录获取新的token"""
        try:
            self.logger.info("尝试重新登录获取token...")
            
            # 登录API
            login_url = f"{self.base_url}/api/auth/login"
            login_data = {
                "email": self.config["login"]["email"],
                "password": self.config["login"]["password"]
            }
            
            response = requests.post(
                login_url, 
                headers=self.base_headers, 
                json=login_data, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 提取token
                new_token = result.get('token') or result.get('access_token')
                if new_token:
                    # 更新配置中的token
                    self.config["auth_token"] = new_token
                    self.save_config()
                    
                    self.logger.info("登录成功，已更新token")
                    
                    # 发送token刷新通知邮件
                    self._send_email_alert(
                        "签到工具Token已刷新",
                        f"登录成功，已自动更新认证token。\n登录时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    
                    return True
                else:
                    self.logger.error(f"登录响应中未找到token: {result}")
                    return False
            else:
                self.logger.error(f"登录失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"登录过程出错: {e}")
            return False
            
    def check_token_validity(self):
        """检查Token有效性"""
        try:
            url = f"{self.base_url}/api/auth/user"
            response = requests.get(url, headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                email = user_data.get('email', 'Unknown')
                self.logger.info(f"Token有效，用户: {email}")
                return True
            elif response.status_code == 401:
                self.logger.warning("Token已失效")
                return False
            else:
                self.logger.error(f"Token验证失败: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Token验证出错: {e}")
            return False
            
    def ensure_valid_token(self):
        """确保token有效，失效时自动重新登录"""
        if self.check_token_validity():
            return True
            
        # Token失效，尝试重新登录
        return self.login_and_get_token()
        
    def perform_checkin(self):
        """执行签到"""
        try:
            # 确保token有效
            if not self.ensure_valid_token():
                return False, {"error": "无法获取有效的认证token"}
                
            url = f"{self.base_url}/api/checkin"
            response = requests.post(url, headers=self.get_auth_headers(), json={}, timeout=10)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success', True):
                        self.logger.info(f"签到成功! 响应: {result}")
                        return True, result
                    else:
                        message = result.get('message', '')
                        if '已签到' in message or '已经签到' in message:
                            self.logger.info("今日已经签到过了")
                            return True, result
                        else:
                            self.logger.error(f"签到失败: {result}")
                            return False, result
                except json.JSONDecodeError:
                    self.logger.info("签到成功! (无JSON响应)")
                    return True, {"message": "签到成功"}
            else:
                try:
                    # 尝试解析错误响应的JSON
                    error_result = response.json()
                    self.logger.error(f"签到失败: {response.status_code} - {response.text}")
                    return False, error_result
                except json.JSONDecodeError:
                    # 如果不是JSON响应，使用原有逻辑
                    self.logger.error(f"签到失败: {response.status_code} - {response.text}")
                    return False, {"error": f"HTTP {response.status_code}", "raw_response": response.text}
                
        except Exception as e:
            self.logger.error(f"签到请求出错: {e}")
            return False, {"error": str(e)}
            
    def get_credits_balance(self):
        """查询积分余额"""
        try:
            url = f"{self.base_url}/api/credits/balance"
            response = requests.get(url, headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"积分查询出错: {e}")
            return None
            
    def _send_email_alert(self, subject, body, alert_type="info"):
        """发送邮件预警"""
        email_config = self.config.get('email_alerts', {})
        
        if not email_config.get('enabled', False):
            return
        
        # 检查必要的邮件配置
        required_fields = ['smtp_server', 'smtp_user', 'smtp_password', 'from_email', 'to_email']
        missing_fields = [field for field in required_fields if not email_config.get(field)]
        
        if missing_fields:
            self.logger.warning(f"邮件配置不完整，缺少字段: {missing_fields}，跳过邮件发送")
            return
            
        try:
            self.logger.info(f"准备发送邮件: {subject}, 类型: {alert_type}")
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = email_config['to_email']
            msg['Subject'] = Header(f"[PVE签到工具] {subject}", 'utf-8')
            
            # 邮件正文
            full_body = f"""
PVE签到工具状态通知

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
类型: {alert_type}

{body}

---
此邮件由PVE签到工具自动发送
配置文件: {self.config_file}
日志文件: {self.log_file}
"""
            
            msg.attach(MIMEText(full_body, 'plain', 'utf-8'))
            
            # 根据端口选择连接方式
            smtp_port = email_config['smtp_port']
            self.logger.info(f"连接SMTP服务器: {email_config['smtp_server']}:{smtp_port}")
            
            if smtp_port == 465:
                # SSL连接
                server = smtplib.SMTP_SSL(email_config['smtp_server'], smtp_port)
                self.logger.info("使用SSL连接")
            else:
                # STARTTLS连接
                server = smtplib.SMTP(email_config['smtp_server'], smtp_port)
                server.starttls()
                self.logger.info("使用STARTTLS连接")
            
            self.logger.info("开始登录SMTP服务器")
            server.login(email_config['smtp_user'], email_config['smtp_password'])
            self.logger.info("SMTP登录成功")
            
            text = msg.as_string()
            server.sendmail(email_config['from_email'], [email_config['to_email']], text)
            server.quit()
            
            self.logger.info(f"邮件发送成功: {subject}")
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            
    def load_status(self):
        """加载运行状态"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def save_status(self, status_data):
        """保存运行状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存状态失败: {e}")
            
    def run_checkin(self):
        """运行签到任务"""
        self.logger.info("=" * 60)
        self.logger.info("开始PVE自动签到任务")
        self.logger.info("=" * 60)
        
        today = datetime.now().strftime("%Y-%m-%d")
        status = self.load_status()
        
        # 检查今天是否已经成功签到
        if today in status and status[today].get("success", False):
            self.logger.info("今日已成功签到，检查是否需要发送成功邮件")
            
            # 如果启用了成功邮件通知，仍然发送邮件
            if self.config['email_alerts'].get('on_success', False):
                self.logger.info("发送今日已签到的成功邮件")
                
                # 获取积分信息
                balance = self.get_credits_balance()
                balance_info = ""
                if balance and 'balance' in balance:
                    balance_data = balance['balance']
                    available = balance_data.get('available', 0)
                    used = balance_data.get('used', 0)
                    total = available + used
                    balance_info = f"\n积分信息:\n  总积分: {total}\n  可用积分: {available}\n  已使用: {used}"
                
                success_msg = f"今日签到状态: 已完成{balance_info}"
                self._send_email_alert(
                    "签到状态确认",
                    success_msg,
                    "success"
                )
            else:
                self.logger.info("成功邮件已禁用，跳过邮件发送")
            
            self.logger.info("任务完成")
            return True
            
        # 获取签到前积分
        before_balance = self.get_credits_balance()
        before_credits = 0
        if before_balance:
            before_credits = before_balance.get('balance', {}).get('available', 0)
            
        # 执行签到
        success, result = self.perform_checkin()
        
        # 记录结果到状态文件
        if today not in status:
            status[today] = {}
            
        status[today].update({
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "result": result
        })
        
        if success:
            # 获取签到后积分
            after_balance = self.get_credits_balance()
            after_credits = before_credits
            earned = 0
            
            if after_balance:
                after_credits = after_balance.get('balance', {}).get('available', 0)
                earned = after_credits - before_credits
                
            if earned > 0:
                # 获取积分详细信息
                balance_info = ""
                if after_balance and 'balance' in after_balance:
                    balance_data = after_balance['balance']
                    available = balance_data.get('available', 0)
                    used = balance_data.get('used', 0)
                    total = available + used
                    balance_info = f"\n积分信息:\n  总积分: {total}\n  可用积分: {available}\n  已使用: {used}"
                
                success_msg = f"签到成功! 获得 {earned} 积分，总积分: {before_credits} -> {after_credits}{balance_info}"
                self.logger.info(success_msg)
                
                # 发送成功邮件（如果启用）
                if self.config['email_alerts'].get('on_success', False):
                    self._send_email_alert(
                        "签到成功",
                        success_msg,
                        "success"
                    )
            else:
                # 获取积分详细信息
                balance_info = ""
                if after_balance and 'balance' in after_balance:
                    balance_data = after_balance['balance']
                    available = balance_data.get('available', 0)
                    used = balance_data.get('used', 0)
                    total = available + used
                    balance_info = f"\n积分信息:\n  总积分: {total}\n  可用积分: {available}\n  已使用: {used}"
                
                self.logger.info("签到完成 (今日已签到)")
                
                # 发送成功邮件（如果启用）
                if self.config['email_alerts'].get('on_success', False):
                    success_msg = f"签到完成 (今日已签到){balance_info}"
                    self._send_email_alert(
                        "签到成功",
                        success_msg,
                        "success"
                    )
                
        else:
            # 提取详细错误信息
            if isinstance(result, dict):
                if result.get('message'):
                    # 检查是否是"已经签到"的情况
                    message = result.get('message', '')
                    if '已签到' in message or '已经签到' in message:
                        # 这种情况视为签到成功
                        self.logger.info(f"今日已签到: {message}")
                        # 更新状态为成功
                        status[today].update({"success": True})
                        
                        # 获取积分信息用于成功邮件
                        after_balance = self.get_credits_balance()
                        balance_info = ""
                        if after_balance and 'balance' in after_balance:
                            balance_data = after_balance['balance']
                            available = balance_data.get('available', 0)
                            used = balance_data.get('used', 0)
                            total = available + used
                            balance_info = f"\n积分信息:\n  总积分: {total}\n  可用积分: {available}\n  已使用: {used}"
                        
                        # 发送成功邮件（根据配置）
                        if self.config['email_alerts'].get('on_success', False):
                            success_msg = f"签到状态: {message}{balance_info}"
                            self._send_email_alert(
                                "签到成功",
                                success_msg,
                                "success"
                            )
                        
                        self.save_status(status)
                        return True
                    else:
                        error_msg = f"签到失败: {message}"
                        detailed_error = f"错误详情: {json.dumps(result, ensure_ascii=False, indent=2)}"
                else:
                    error_msg = f"签到失败: {result}"
                    detailed_error = f"错误详情: {json.dumps(result, ensure_ascii=False, indent=2)}"
            else:
                error_msg = f"签到失败: {result}"
                detailed_error = f"错误详情: {str(result)}"
                
            self.logger.error(error_msg)
            
            # 发送失败邮件
            if self.config['email_alerts'].get('on_failure', True):
                self._send_email_alert(
                    "签到失败",
                    f"{error_msg}\n\n{detailed_error}\n\n请检查网络连接和配置是否正确。",
                    "error"
                )
                
        # 保存状态
        self.save_status(status)
        
        return success
    
    def test_email(self):
        """测试邮件发送功能"""
        self.logger.info("开始测试邮件发送功能")
        
        # 获取积分信息用于测试
        balance = self.get_credits_balance()
        balance_info = ""
        if balance and 'balance' in balance:
            balance_data = balance['balance']
            available = balance_data.get('available', 0)
            used = balance_data.get('used', 0)
            total = available + used
            balance_info = f"\n积分信息:\n  总积分: {total}\n  可用积分: {available}\n  已使用: {used}"
        
        test_msg = f"这是一封测试邮件，用于验证PVE签到工具的邮件功能是否正常。{balance_info}\n\n如果收到此邮件，说明邮件配置正确。"
        
        self._send_email_alert(
            "邮件功能测试",
            test_msg,
            "test"
        )
        
        self.logger.info("邮件测试完成，请检查收件箱")
        return True

def main():
    """主函数 - 适合crontab调用"""
    # 解析命令行参数
    config_path = None
    test_mode = False
    test_email = False
    
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == '--test':
            test_mode = True
        elif arg == '--test-email':
            test_email = True
        elif arg == '--config' and i + 1 < len(sys.argv):
            config_path = sys.argv[i + 1]
        elif arg.startswith('--config='):
            config_path = arg.split('=', 1)[1]
    
    try:
        # 创建签到实例
        checkin = PVECheckinCron(config_path)
        
        if test_mode:
            print("PVE Checkin Tool Test Mode")
            print(f"Config: {checkin.config_file}")
            print(f"Status: {checkin.status_file}")
            print(f"Log: {checkin.log_file}")
            print("-" * 50)
        
        if test_email:
            print("PVE Checkin Tool Email Test Mode")
            print(f"Config: {checkin.config_file}")
            print("-" * 50)
            # 测试邮件发送
            success = checkin.test_email()
            print(f"Email Test Result: {'Success' if success else 'Failed'}")
            print("请检查收件箱中是否收到测试邮件")
            sys.exit(0 if success else 1)
            
        # 运行签到
        success = checkin.run_checkin()
        
        if test_mode:
            print(f"Result: {'Success' if success else 'Failed'}")
            print(f"Log saved to: {checkin.log_file}")
            
        # 返回适当的退出码
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Program error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()