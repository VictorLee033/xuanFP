# -*- coding: utf-8 -*-
"""SMTP 邮件发送（QQ/163 等邮箱，SSL 465）。"""
import logging
import smtplib
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr

logger = logging.getLogger(__name__)


def send_email(sender: str, auth_code: str, recipient: str,
               subject: str, html: str, host: str = "smtp.qq.com",
               port: int = 465) -> None:
    """通过 SMTP SSL 发送 HTML 邮件。失败抛异常由调用方处理。"""
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = formataddr((str(Header("xuanFP 智能股票工作台", "utf-8")), sender))
    msg["To"] = recipient
    with smtplib.SMTP_SSL(host, port, timeout=30) as s:
        s.login(sender, auth_code)
        s.sendmail(sender, [recipient], msg.as_string())
    logger.info("邮件已发送: %s -> %s", sender, recipient)
