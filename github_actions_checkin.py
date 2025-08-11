#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions版本的自动签到工具 - mirror.o3pro.pro
专为GitHub Actions环境优化，去除了文件权限和路径依赖
"""

import requests
import json
import logging
import smtplib
import os
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

class GitHubActionsCheckin:
    def __init__(self):
        self.config_file = "pve_checkin_config.json"
        self.base_url = "https://mirror.o3pro.pro"
        
        # 加载配置
        self.load_config()
        
        # 设置日志 - GitHub Actions优化
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
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"配置文件读取失败: {e}")
                sys.exit(1)
        else:
            print(f"配置文件 {self.config_file} 不存在")
            sys.exit(1)
            
    def setup_logging(self):
        """配置日志系统 - GitHub Actions优化"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # GitHub Actions环境使用标准输出
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f"pve_checkin_{datetime.now().strftime('%Y%m')}.log", encoding='utf-8')
            ],
            force=True
        )
        
        self.logger = logging.getLogger(__name__)
        
    def get_auth_headers(self):
        """获取带认证的请求头"""
        headers = self.base_headers.copy()
        headers['Authorization'] = f'Bearer {self.config["auth_token"]}'
        return headers
        
    def login_and_get_token(self):
        """登录获取新的token"""
        try:
            self.logger.info("尝试重新登录获取token...")
            
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
                new_token = result.get('token') or result.get('access_token')
                if new_token:
                    self.config["auth_token"] = new_token
                    self.logger.info("登录成功，已更新token")
                    
                    # 发送token刷新通知邮件
                    if self.config['email_alerts'].get('on_token_refresh', True):
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
        return self.login_and_get_token()
        
    def perform_checkin(self):
        """执行签到"""
        try:
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
                    error_result = response.json()
                    self.logger.error(f"签到失败: {response.status_code} - {response.text}")
                    return False, error_result
                except json.JSONDecodeError:
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
        """发送邮件预警 - GitHub Actions版本"""
        email_config = self.config.get('email_alerts', {})
        
        if not email_config.get('enabled', False):
            self.logger.info("邮件通知已禁用")
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
            msg['Subject'] = Header(f"[GitHub Actions签到] {subject}", 'utf-8')
            
            # 邮件正文
            full_body = f"""
GitHub Actions自动签到通知

时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
类型: {alert_type}
运行环境: GitHub Actions

{body}

---
此邮件由GitHub Actions自动发送
Repository: {os.environ.get('GITHUB_REPOSITORY', 'Unknown')}
Run ID: {os.environ.get('GITHUB_RUN_ID', 'Unknown')}
"""
            
            msg.attach(MIMEText(full_body, 'plain', 'utf-8'))
            
            # 发送邮件
            smtp_port = email_config['smtp_port']
            self.logger.info(f"连接SMTP服务器: {email_config['smtp_server']}:{smtp_port}")
            
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(email_config['smtp_server'], smtp_port)
            else:
                server = smtplib.SMTP(email_config['smtp_server'], smtp_port)
                server.starttls()
            
            server.login(email_config['smtp_user'], email_config['smtp_password'])
            text = msg.as_string()
            server.sendmail(email_config['from_email'], [email_config['to_email']], text)
            server.quit()
            
            self.logger.info(f"邮件发送成功: {subject}")
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
            
    def run_checkin(self):
        """运行签到任务 - GitHub Actions版本"""
        self.logger.info("=" * 60)
        self.logger.info("开始GitHub Actions自动签到任务")
        self.logger.info("=" * 60)
        
        # 获取签到前积分
        before_balance = self.get_credits_balance()
        before_credits = 0
        if before_balance:
            before_credits = before_balance.get('balance', {}).get('available', 0)
            
        # 执行签到
        success, result = self.perform_checkin()
        
        if success:
            # 获取签到后积分
            after_balance = self.get_credits_balance()
            after_credits = before_credits
            earned = 0
            
            if after_balance:
                after_credits = after_balance.get('balance', {}).get('available', 0)
                earned = after_credits - before_credits
                
            if earned > 0:
                balance_info = ""
                if after_balance and 'balance' in after_balance:
                    balance_data = after_balance['balance']
                    available = balance_data.get('available', 0)
                    used = balance_data.get('used', 0)
                    total = available + used
                    balance_info = f"\n积分信息:\n  总积分: {total}\n  可用积分: {available}\n  已使用: {used}"
                
                success_msg = f"签到成功! 获得 {earned} 积分，总积分: {before_credits} -> {after_credits}{balance_info}"
                self.logger.info(success_msg)
                
                if self.config['email_alerts'].get('on_success', False):
                    self._send_email_alert("签到成功", success_msg, "success")
            else:
                message = result.get('message', '')
                if '已签到' in message or '已经签到' in message:
                    self.logger.info(f"今日已签到: {message}")
                    if self.config['email_alerts'].get('on_success', False):
                        self._send_email_alert("签到状态", f"签到状态: {message}", "success")
                
        else:
            error_msg = f"签到失败: {result}"
            self.logger.error(error_msg)
            
            if self.config['email_alerts'].get('on_failure', True):
                self._send_email_alert("签到失败", f"{error_msg}\n\n请检查GitHub Actions日志了解详细信息。", "error")
                
        return success

def main():
    """主函数 - GitHub Actions版本"""
    test_mode = '--test' in sys.argv
    
    try:
        checkin = GitHubActionsCheckin()
        
        if test_mode:
            print("GitHub Actions Checkin Tool Test Mode")
            print(f"Config: {checkin.config_file}")
            print("-" * 50)
        
        success = checkin.run_checkin()
        
        if test_mode:
            print(f"Result: {'Success' if success else 'Failed'}")
            
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"Program error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()