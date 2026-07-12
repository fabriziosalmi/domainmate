# Shared constants used across monitors and services.

# ── Status values ────────────────────────────────────────────────────────────
STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"
STATUS_ERROR = "error"

# ── Expiry thresholds (days) ─────────────────────────────────────────────────
EXPIRY_WARNING_DAYS = 30
EXPIRY_CRITICAL_DAYS = 7

# ── HTTP / network timeouts (seconds) ───────────────────────────────────────
TIMEOUT_SOCKET = 5.0          # Generic socket connections
TIMEOUT_WEAK_PROTO = 2.0      # Weak-protocol probe (aggressive, intentional)
TIMEOUT_HTTP = 10             # aiohttp client sessions
TIMEOUT_CLI_HTTP = 15         # CLI heartbeat / api_url uploads

# ── RBL magic return-code constants ─────────────────────────────────────────
# Spamhaus/CBL: prefix returned when a public-DNS resolver blocks the DNSBL query
RBL_BLOCKED_PREFIX = "127.255.255."
# PBL/Policy listings: indicate dynamic or consumer IP space — not actionable
RBL_PBL_IPS = frozenset({"127.0.0.10", "127.0.0.11"})

# ── Default RBL list (override via config.yaml: monitors.blacklist.rbls) ─────
DEFAULT_RBLS = [
    "zen.spamhaus.org",
    "bl.spamcop.net",
    "cbl.abuseat.org",
    "dnsbl.sorbs.net",
    "b.barracudacentral.org",
    "dnsbl-1.uceprotect.net",
]
