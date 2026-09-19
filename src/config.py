"""
Configuration loading and validation, shared by the CLI and the API.

Every key documented in README.md and config.yaml is read from here, so a
setting that appears in the file actually reaches the monitor that uses it.
Keys that are not recognised are reported rather than ignored: silently
dropping a typo is how a monitoring tool ends up watching the wrong thing.
"""

import os
from typing import Any, Optional

import yaml
from loguru import logger

DEFAULT_CONFIG_FILE = "config.yaml"

# Keys recognised at the top level and inside each monitors.<name> section.
_KNOWN_TOP_LEVEL = frozenset({
    "domains", "monitors", "reports", "notifications",
    "heartbeat_url", "api_url",
})

_KNOWN_MONITOR_KEYS = {
    "domain": frozenset({"enabled", "expiry_warning_days", "expiry_critical_days",
                         "use_rdap"}),
    "ssl": frozenset({"enabled", "expiry_warning_days", "expiry_critical_days"}),
    "dns": frozenset({"enabled", "required_records"}),
    "security": frozenset({"enabled"}),
    "blacklist": frozenset({"enabled", "rbls"}),
}

_KNOWN_REPORT_KEYS = frozenset({"output_dir", "retention_days"})


def config_path(cli_path: Optional[str] = None) -> str:
    """
    Resolve which config file to read.

    Priority: DOMAINMATE_CONFIG_FILE, then the CLI flag, then the default.
    """
    return os.environ.get("DOMAINMATE_CONFIG_FILE") or cli_path or DEFAULT_CONFIG_FILE


def load_config(path: Optional[str] = None) -> dict:
    """
    Read and parse the config file. Raises on an unreadable or malformed file;
    callers decide whether that is fatal.
    """
    resolved = config_path(path)
    with open(resolved, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ValueError(f"{resolved}: expected a mapping at the top level")

    logger.info(f"Loaded config from {resolved}")
    validate_config(config)
    return config


def validate_config(config: dict) -> list:
    """
    Warn about keys that no code reads, and return them.

    A setting that looks applied but is not is worse than one that errors, so
    every unrecognised key gets a line in the log naming where it sits.
    """
    unknown = []

    def flag(where: str, key: str):
        unknown.append(f"{where}{key}")
        logger.warning(f"Unknown config key ignored: {where}{key}")

    for key in config:
        if key not in _KNOWN_TOP_LEVEL:
            flag("", key)

    monitors = config.get("monitors") or {}
    if isinstance(monitors, dict):
        for name, section in monitors.items():
            if name not in _KNOWN_MONITOR_KEYS:
                flag("monitors.", name)
                continue
            if not isinstance(section, dict):
                continue
            for key in section:
                if key not in _KNOWN_MONITOR_KEYS[name]:
                    flag(f"monitors.{name}.", key)

    reports = config.get("reports") or {}
    if isinstance(reports, dict):
        for key in reports:
            if key not in _KNOWN_REPORT_KEYS:
                flag("reports.", key)

    # Unsupported entries in required_records are reported by DNSMonitor itself,
    # so the warning fires once wherever the monitor is built from.

    return unknown


def monitor_config(config: dict, name: str) -> dict:
    """Return the monitors.<name> section, or an empty dict."""
    section = (config.get("monitors") or {}).get(name)
    return section if isinstance(section, dict) else {}


def monitor_enabled(config: dict, name: str) -> bool:
    return bool(monitor_config(config, name).get("enabled", False))


def report_setting(config: dict, key: str, default: Any = None) -> Any:
    reports = config.get("reports")
    if not isinstance(reports, dict):
        return default
    return reports.get(key, default)
