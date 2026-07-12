import aiohttp
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict
from github import Github
import gitlab
from loguru import logger
from src.constants import TIMEOUT_HTTP

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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = NotificationSettings()

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=TIMEOUT_HTTP)

# Allowed URL schemes for webhook / external URLs
_ALLOWED_SCHEMES = {"https"}


def _validate_webhook_url(url: str) -> str:
    """
    Validate that a webhook URL:
    - uses HTTPS (prevents credential exposure over plain HTTP)
    - has a non-empty hostname (prevents SSRF to bare IPs / localhost)

    Returns the URL unchanged if valid; raises ValueError otherwise.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Webhook URL must use HTTPS, got scheme '{parsed.scheme}'"
        )
    if not parsed.hostname:
        raise ValueError("Webhook URL is missing a hostname")
    return url


class NotificationService:
    def __init__(self, config: dict = None):
        """
        Initialize notification service.
        Priority: Env Vars (settings) > Config YAML > None
        """
        self.config = config or {}
        
    def _get_config_value(self, channel: str, key: str, env_value: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a config value, preferring env var over YAML config.
        """
        return env_value or self.config.get("notifications", {}).get(channel, {}).get(key)

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
        token = self._get_config_value("github", "token", settings.GITHUB_TOKEN)
        repo_name = self._get_config_value("github", "repo", settings.GITHUB_REPO)
        
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
        token = self._get_config_value("gitlab", "token", settings.GITLAB_TOKEN)
        pid = self._get_config_value("gitlab", "project_id", settings.GITLAB_PROJECT_ID)
        
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
        token = self._get_config_value("telegram", "bot_token", settings.TELEGRAM_BOT_TOKEN)
        chat_id = self._get_config_value("telegram", "chat_id", settings.TELEGRAM_CHAT_ID)
        
        if not (token and chat_id):
            return
            
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": f"*{title}*\n\n{message}",
                "parse_mode": "Markdown"
            }
            async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
            logger.info("Telegram message sent.")
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")

    async def _send_teams(self, title: str, message: str, level: str):
        raw_url = self._get_config_value("teams", "webhook_url", settings.TEAMS_WEBHOOK_URL)

        if not raw_url:
            return

        try:
            url = _validate_webhook_url(raw_url)
        except ValueError as e:
            logger.error(f"Teams webhook URL rejected: {e}")
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
            async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
            logger.info("Teams webhook sent.")
        except Exception as e:
            logger.error(f"Teams notification failed: {e}")

    async def _send_email(self, title: str, body: str):
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
        raw_url = self._get_config_value("webhook", "url", settings.GENERIC_WEBHOOK_URL)

        if not raw_url:
            return

        try:
            url = _validate_webhook_url(raw_url)
        except ValueError as e:
            logger.error(f"Generic webhook URL rejected: {e}")
            return

        try:
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            async with aiohttp.ClientSession(timeout=HTTP_TIMEOUT) as session:
                async with session.post(url, json=payload) as resp:
                    resp.raise_for_status()
            logger.info("Generic Webhook sent.")
        except Exception as e:
            logger.error(f"Generic Webhook failed: {e}")

if __name__ == "__main__":
    # Test
    import asyncio
    s = NotificationService()
    asyncio.run(s.send_notification("Test Alert", "This is a test from DomainMate.", "info"))
