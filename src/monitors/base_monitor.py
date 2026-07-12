from abc import ABC, abstractmethod
from loguru import logger
from src.constants import (
    STATUS_OK, STATUS_WARNING, STATUS_CRITICAL, STATUS_ERROR,
    EXPIRY_WARNING_DAYS, EXPIRY_CRITICAL_DAYS,
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

    @staticmethod
    def get_expiry_status(days: int,
                          warning_threshold: int = EXPIRY_WARNING_DAYS,
                          critical_threshold: int = EXPIRY_CRITICAL_DAYS) -> str:
        """
        Return STATUS_OK / STATUS_WARNING / STATUS_CRITICAL based on days left.
        Shared by DomainMonitor and SSLMonitor.
        """
        if days < critical_threshold:
            return STATUS_CRITICAL
        if days < warning_threshold:
            return STATUS_WARNING
        return STATUS_OK
