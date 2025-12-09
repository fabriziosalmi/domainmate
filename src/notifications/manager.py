import json
import os
import hashlib
from datetime import datetime, timedelta
from loguru import logger
from collections import defaultdict
from src.notifications.service import NotificationService

class NotificationManager:
    def __init__(self, config: dict, state_file: str = "reports/notification_state.json"):
        self.config = config
        self.state_file = state_file
        self.service = NotificationService(config)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load notification state: {e}")
        return {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save notification state: {e}")

    def _get_issue_id(self, result: dict) -> str:
        """Create a unique ID for an issue (Domain + Monitor Type)."""
        return f"{result['domain']}:{result['monitor']}"

    def process_and_send(self, results: list):
        """
        Process scan results, update state, aggregate, and send notifications.
        """
        # 1. Identify current issues
        current_issues = {}
        alerts_to_send = []

        for res in results:
            if res.get("status") in ["critical", "error", "warning"]:
                issue_id = self._get_issue_id(res)
                current_issues[issue_id] = res

                # Check state
                if issue_id in self.state:
                    data = self.state[issue_id]
                    last_sent = datetime.fromisoformat(data["last_sent"])
                    
                    # Policy: Only resend if > 24h passed
                    if datetime.now() - last_sent > timedelta(hours=24):
                        data["count"] += 1
                        data["last_sent"] = datetime.now().isoformat()
                        res["alert_count"] = data["count"] # Inject count for msg
                        alerts_to_send.append(res)
                        logger.info(f"Resending alert for {issue_id} (Count: {data['count']})")
                    else:
                        logger.info(f"Snoozing alert for {issue_id} (Sent {last_sent})")
                else:
                    # New Issue
                    self.state[issue_id] = {
                        "first_seen": datetime.now().isoformat(),
                        "last_sent": datetime.now().isoformat(),
                        "count": 1,
                        "monitor": res["monitor"],
                        "domain": res["domain"]
                    }
                    res["alert_count"] = 1
                    alerts_to_send.append(res)

        # 2. Cleanup Resolved Issues (Optional: Send 'Fixed' notification?)
        # For now, just remove from state so if it reappears, count resets.
        # Or keep it for history? Let's remove to keep file small.
        ids_to_remove = []
        for issue_id in self.state:
            if issue_id not in current_issues:
                logger.success(f"Issue resolved: {issue_id}")
                ids_to_remove.append(issue_id)
        
        for i in ids_to_remove:
            del self.state[i]

        self._save_state()

        # 3. Aggregate by Domain
        if not alerts_to_send:
            logger.info("No new alerts to send.")
            return

        domain_groups = defaultdict(list)
        for alert in alerts_to_send:
            domain_groups[alert["domain"]].append(alert)

        # 4. Send Aggregated Messages
        for domain, alerts in domain_groups.items():
            self._send_aggregated_alert(domain, alerts)

    def _send_aggregated_alert(self, domain: str, alerts: list):
        """Constructs a digest message for the domain."""
        title = f"🚨 Security Alert: {domain}"
        lines = [f"Found {len(alerts)} issues for **{domain}**:"]
        
        for alert in alerts:
            icon = "🔴" if alert.get("status") == "critical" else "⚠️"
            cnt = f"(Repeated {alert.get('alert_count')}x)" if alert.get("alert_count", 0) > 1 else "(New)"
            lines.append(f"{icon} **{alert['monitor'].upper()}**: {alert.get('message', 'Unknown Error')} {cnt}")
            if "details" in alert:
                 # If details is list, join it
                 dets = alert['details']
                 if isinstance(dets, list):
                     for d in dets[:3]: # Limit detail lines
                         lines.append(f"   - {d}")
                 elif isinstance(dets, str):
                      lines.append(f"   - {dets}")

        message = "\n".join(lines)
        self.service.send(title, message)
