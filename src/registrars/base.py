from abc import ABC, abstractmethod
from typing import Dict, Any

class RegistrarProvider(ABC):
    """
    Abstract Base Class for Domain Registrar integrations.
    Each provider must implement these methods.
    """
    
    @abstractmethod
    def get_domain_details(self, domain: str) -> Dict[str, Any]:
        """
        Retrieve details for a specific domain.
        Should return: {'domain': str, 'expires': datetime, 'auto_renew': bool, 'status': str}
        """
        pass

    @abstractmethod
    def list_domains(self) -> list:
        """
        List all domains owned in this account.
        """
        pass

    @abstractmethod
    def renew_domain(self, domain: str, years: int = 1) -> bool:
        """
        Attempt to renew the domain.
        Returns True if successful, False otherwise.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
