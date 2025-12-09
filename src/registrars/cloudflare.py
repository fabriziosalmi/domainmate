import requests
import os
from .base import RegistrarProvider
from typing import Dict, Any, Optional
from loguru import logger

class CloudflareProvider(RegistrarProvider):
    def __init__(self):
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.email = os.getenv("CLOUDFLARE_EMAIL")
        self.api_key = os.getenv("CLOUDFLARE_API_KEY") # Legacy
        self.base_url = "https://api.cloudflare.com/client/v4"

    @property
    def provider_name(self) -> str:
        return "Cloudflare"

    def _get_headers(self) -> dict:
        if self.api_token:
            return {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        elif self.email and self.api_key:
             return {
                 "X-Auth-Email": self.email,
                 "X-Auth-Key": self.api_key,
                 "Content-Type": "application/json"
             }
        else:
             logger.warning("No Cloudflare credentials found.")
             return {}

    def list_domains(self) -> list:
        try:
            url = f"{self.base_url}/zones"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                     return [zone["name"] for zone in data.get("result", [])]
            logger.error(f"Cloudflare list_domains failed: {response.text}")
            return []
        except Exception as e:
            logger.error(f"Error listing Cloudflare domains: {e}")
            return []

    def get_domain_details(self, domain: str) -> Dict[str, Any]:
        # Implementation note: Cloudflare splits 'Registrar' from 'Zones'.
        # This assumes we are querying the Registrar endpoints or approximating from Zone info.
        # Direct Registrar API usage for expiration requires 'Account' permissions.
        # Below is a simplified implementation primarily using Zone info, 
        # which might not have exact 'registrar' expiry if not bought on CF, 
        # but commonly used for CF managed domains.
        
        # 1. Get Zone ID
        zone_id = self._get_zone_id(domain)
        if not zone_id:
            return {}

        # 2. Registrar details (mocking the specific registrar endpoint as it varies by plan)
        # Real endpoint: GET accounts/:account_identifier/registrar/domains/:domain_name
        return {
            "domain": domain,
            "status": "ACTIVE", # simplified
            "auto_renew": True, # default assumption or extra API call
            "message": "Detailed registrar info requires Account ID scope"
        }

    def renew_domain(self, domain: str, years: int = 1) -> bool:
        logger.info(f"Cloudflare renewal for {domain} requested (Not fully implemented in public API wrappers usually)")
        return False

    def _get_zone_id(self, domain: str) -> Optional[str]:
        try:
            url = f"{self.base_url}/zones?name={domain}"
            response = requests.get(url, headers=self._get_headers())
            data = response.json()
            if data["success"] and data["result"]:
                return data["result"][0]["id"]
        except Exception:
            pass
        return None
