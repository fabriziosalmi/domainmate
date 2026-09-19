from abc import ABC, abstractmethod

from loguru import logger

from src.constants import (
    EXPIRY_CRITICAL_DAYS,
    EXPIRY_WARNING_DAYS,
    STATUS_CRITICAL,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARNING,
)


class BaseMonitor(ABC):
    """
    Abstract base class for all domain monitors.

    Subclasses must define ``monitor_name`` and implement ``_run_check()``.
    The public ``check()`` method wraps ``_run_check()`` in a standardised
    error handler so every monitor returns a consistent result dict.
    """

    #: Override in each subclass (e.g. "domain", "ssl", …)
    monitor_name: str = "base"

    def __init__(self,
                 expiry_warning_days: int = EXPIRY_WARNING_DAYS,
                 expiry_critical_days: int = EXPIRY_CRITICAL_DAYS):
        self.expiry_warning_days = expiry_warning_days
        self.expiry_critical_days = expiry_critical_days

    @classmethod
    def from_config(cls, cfg: dict = None):
        """
        Build the monitor from its ``monitors.<name>`` config section.
        Subclasses that read other keys override this.
        """
        cfg = cfg or {}
        return cls(
            expiry_warning_days=cfg.get("expiry_warning_days", EXPIRY_WARNING_DAYS),
            expiry_critical_days=cfg.get("expiry_critical_days", EXPIRY_CRITICAL_DAYS),
        )

    # ── Public entry-point ────────────────────────────────────────────────────

    def check(self, domain: str) -> dict:
        """Run the monitor and guarantee a well-formed result dict."""
        try:
            return self._run_check(domain)
        except Exception as e:
            logger.error(f"Error in {self.monitor_name} monitor for {domain}: {e}")
            return self._error_result("Check failed")

    # ── Abstract method ───────────────────────────────────────────────────────

    @abstractmethod
    def _run_check(self, domain: str) -> dict:
        """Perform the actual check logic; raise on unrecoverable errors."""

    # ── Shared helpers ────────────────────────────────────────────────────────

    def _ok_result(self, message: str, **extra) -> dict:
        return {"monitor": self.monitor_name, "status": STATUS_OK,
                "message": message, **extra}

    def _warning_result(self, message: str, **extra) -> dict:
        return {"monitor": self.monitor_name, "status": STATUS_WARNING,
                "message": message, **extra}

    def _critical_result(self, message: str, **extra) -> dict:
        return {"monitor": self.monitor_name, "status": STATUS_CRITICAL,
                "message": message, **extra}

    def _error_result(self, message: str, **extra) -> dict:
        return {"monitor": self.monitor_name, "status": STATUS_ERROR,
                "message": message, **extra}

    def get_expiry_status(self, days: int) -> str:
        """
        Return STATUS_OK / STATUS_WARNING / STATUS_CRITICAL based on days left,
        using this instance's thresholds. Shared by DomainMonitor and SSLMonitor.
        """
        if days < self.expiry_critical_days:
            return STATUS_CRITICAL
        if days < self.expiry_warning_days:
            return STATUS_WARNING
        return STATUS_OK
