import os
import aiohttp
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import List, Optional
from pydantic_settings import BaseSettings
from github import Github
import gitlab
from loguru import logger

class NotificationSettings(BaseSettings):
    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO: Optional[str] = None # user/repo
    
    # GitLab
    GITLAB_URL: str = "https://gitlab.com"
    GITLAB_TOKEN: Optional[str] = None
    GITLAB_PROJECT_ID: Optional[str] = None
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Teams
    TEAMS_WEBHOOK_URL: Optional[str] = None
    
    # Email
    EMAIL_SMTP_SERVER: Optional[str] = None
    EMAIL_SMTP_PORT: int = 587
    EMAIL_USER: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    EMAIL_TO: Optional[str] = None

    # Generic Webhook
    GENERIC_WEBHOOK_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = NotificationSettings()

class NotificationService:
    def __init__(self, config: dict = None):
        """
        Initialize notification service.
        Priority: Env Vars (settings) > Config YAML > None
        """
        self.config = config or {}
        
    async def send_notification(self, title: str, message: str, level: str = "info"):
        """
        Send notification to all configured channels.
        """
        logger.info(f"Sending notification: {title} [{level}]")
        
        await self._send_github_issue(title, message, level)
        await self._send_gitlab_issue(title, message, level)
        await self._send_telegram(title, message)
        await self._send_teams(title, message, level)
        await self._send_email(title, message)
        await self._send_webhook(title, message, level)

    async def _send_github_issue(self, title: str, body: str, level: str):
        token = settings.GITHUB_TOKEN or self.config.get("notifications", {}).get("github", {}).get("token")
        repo_name = settings.GITHUB_REPO or self.config.get("notifications", {}).get("github", {}).get("repo")
        
        if not (token and repo_name and level == "critical"):
            return
            
        try:
            g = Github(token)
            repo = g.get_repo(repo_name)
            repo.create_issue(title=f"[{level.upper()}] {title}", body=body, labels=[level])
            logger.info("GitHub Issue created.")
        except Exception as e:
            logger.error(f"GitHub notification failed: {e}")

    async def _send_gitlab_issue(self, title: str, body: str, level: str):
        token = settings.GITLAB_TOKEN or self.config.get("notifications", {}).get("gitlab", {}).get("token")
        pid = settings.GITLAB_PROJECT_ID or self.config.get("notifications", {}).get("gitlab", {}).get("project_id")
        
        if not (token and pid and level == "critical"):
            return
            
        try:
            gl = gitlab.Gitlab(settings.GITLAB_URL, private_token=token)
            project = gl.projects.get(pid)
            project.issues.create({'title': f"[{level.upper()}] {title}", 'description': body})
            logger.info("GitLab Issue created.")
        except Exception as e:
            logger.error(f"GitLab notification failed: {e}")

    async def _send_telegram(self, title: str, message: str):
        token = settings.TELEGRAM_BOT_TOKEN or self.config.get("notifications", {}).get("telegram", {}).get("bot_token")
        chat_id = settings.TELEGRAM_CHAT_ID or self.config.get("notifications", {}).get("telegram", {}).get("chat_id")
        
        if not (token and chat_id):
            return
            
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": f"*{title}*\n\n{message}",
                "parse_mode": "Markdown"
            }
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload)
            logger.info("Telegram message sent.")
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")

    async def _send_teams(self, title: str, message: str, level: str):
        url = settings.TEAMS_WEBHOOK_URL or self.config.get("notifications", {}).get("teams", {}).get("webhook_url")
        
        if not url:
            return
            
        try:
            color = "FF0000" if level == "critical" else "00FF00"
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color,
                "summary": title,
                "sections": [{
                    "activityTitle": title,
                    "activitySubtitle": f"Level: {level}",
                    "text": message
                }]
            }
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload)
            logger.info("Teams webhook sent.")
        except Exception as e:
            logger.error(f"Teams notification failed: {e}")

    async def _send_email(self, title: str, body: str):
        # Email config is complex, usually prefer ENV but support config too
        srv = settings.EMAIL_SMTP_SERVER
        to = settings.EMAIL_TO
        
        if not (srv and to):
            return
            
        try:
            msg = EmailMessage()
            msg.set_content(body)
            msg['Subject'] = title
            msg['From'] = settings.EMAIL_FROM or "monitor@domainmate.local"
            msg['To'] = to

            with smtplib.SMTP(settings.EMAIL_SMTP_SERVER, settings.EMAIL_SMTP_PORT) as server:
                if settings.EMAIL_USER and settings.EMAIL_PASSWORD:
                    server.starttls()
                    server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
                server.send_message(msg)
            logger.info("Email sent.")
        except Exception as e:
            logger.error(f"Email notification failed: {e}")

    async def _send_webhook(self, title: str, message: str, level: str):
        url = settings.GENERIC_WEBHOOK_URL or self.config.get("notifications", {}).get("webhook", {}).get("url")
        
        if not url:
            return
            
        try:
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat()
            }
            async with aiohttp.ClientSession() as session:
                await session.post(url, json=payload)
            logger.info("Generic Webhook sent.")
        except Exception as e:
            logger.error(f"Generic Webhook failed: {e}")

if __name__ == "__main__":
    # Test
    import asyncio
    s = NotificationService()
    asyncio.run(s.send_notification("Test Alert", "This is a test from DomainMate.", "info"))
