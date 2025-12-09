import requests
import os
from .base import RegistrarProvider
from typing import Dict, Any
from loguru import logger

class GoDaddyProvider(RegistrarProvider):
    def __init__(self):
        self.api_key = os.getenv("GODADDY_API_KEY")
        self.api_secret = os.getenv("GODADDY_API_SECRET")
        # Use OTE (test) environment by default for safety, switch to prod in env
        self.is_prod = os.getenv("GODADDY_ENV", "dev").lower() == "prod"
        self.base_url = "https://api.godaddy.com/v1" if self.is_prod else "https://api.ote-godaddy.com/v1"

    @property
    def provider_name(self) -> str:
        return "GoDaddy"

    def _get_headers(self) -> dict:
        if self.api_key and self.api_secret:
            return {
                "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
                "Content-Type": "application/json"
            }
        logger.warning("No GoDaddy credentials found.")
        return {}

    def list_domains(self) -> list:
        try:
            url = f"{self.base_url}/domains"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                # Returns list of dicts
                return [d["domain"] for d in response.json()]
            logger.error(f"GoDaddy list_domains failed: {response.text}")
            return []
        except Exception as e:
            logger.error(f"Error listing GoDaddy domains: {e}")
            return []

    def get_domain_details(self, domain: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/domains/{domain}"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                data = response.json()
                return {
                    "domain": data.get("domain"),
                    "expires": data.get("expires"),
                    "auto_renew": data.get("renewAuto"),
                    "status": data.get("status"),
                    "locked": data.get("locked")
                }
            return {"error": f"Failed to get details: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def renew_domain(self, domain: str, years: int = 1) -> bool:
        # POST /v1/domains/{domain}/renew
        try:
            url = f"{self.base_url}/domains/{domain}/renew"
            payload = {"period": years}
            response = requests.post(url, json=payload, headers=self._get_headers())
            if response.status_code == 200:
                logger.success(f"Successfully renewed {domain}")
                return True
            logger.error(f"Failed to renew {domain}: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Exception during renewal of {domain}: {e}")
            return False
