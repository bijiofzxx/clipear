"""Email 通知模块"""


import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Notifier:
    """多渠道通知"""
    
    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger if logger else logging.getLogger(__name__)
    
    def send(self, subject: str, content: str):
        """发送邮件"""
        try:
            email_config = dict(sender=self.config.sender,
                                smtp_server=self.config.smtp_server,
                                smtp_port=self.config.smtp_port,
                                password=self.config.password,
                                receivers=self.config.receivers)
            
            msg = MIMEMultipart()
            msg['From'] = email_config['sender']
            msg['To'] = ', '.join(email_config['receivers'])
            msg['Subject'] = subject
            
            # HTML格式
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
{content}
                </pre>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            # 发送
            with smtplib.SMTP_SSL(
                email_config['smtp_server'], 
                email_config['smtp_port'], timeout=10) as server:
                server.login(email_config['sender'], email_config['password'])
                server.send_message(msg)
            
            self.logger.info(f"✓ 邮件已发送: {subject}")
            
        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
