import glob
import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

TEMPLATE_NAME = "report.html"

#: One JSON snapshot per run, so a scan can be compared against earlier ones.
#: index.html and report.json always describe the latest run.
HISTORY_PREFIX = "report-"
HISTORY_STAMP = "%Y%m%d-%H%M%S"
_HISTORY_RE = re.compile(r"^report-(\d{8}-\d{6})\.json$")

#: The template shipped with the package. It is a real file rather than a
#: string literal so it can be reviewed in a diff and edited in place.
PACKAGED_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


class HTMLGenerator:
    def __init__(self, template_dir: str = None, output_dir: str = "reports",
                 retention_days: int = None):
        self.output_dir = output_dir
        self.template_dir = template_dir or PACKAGED_TEMPLATE_DIR
        # From config.yaml: reports.retention_days. None keeps every snapshot.
        self.retention_days = retention_days
        os.makedirs(output_dir, exist_ok=True)
        self._ensure_template()
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def _ensure_template(self):
        """
        Seed a custom template directory from the packaged template, and never
        touch one that already exists.

        This used to rewrite report.html unconditionally on every run, which
        silently destroyed any customisation the moment the tool was used.
        """
        os.makedirs(self.template_dir, exist_ok=True)
        target = os.path.join(self.template_dir, TEMPLATE_NAME)
        if os.path.exists(target):
            return

        source = os.path.join(PACKAGED_TEMPLATE_DIR, TEMPLATE_NAME)
        if os.path.abspath(source) == os.path.abspath(target):
            raise FileNotFoundError(
                f"The packaged template is missing from {source}. "
                f"This is a broken installation, not a configuration problem."
            )

        shutil.copyfile(source, target)
        logger.info(f"Seeded report template at {target}; edits to it are kept.")

    def generate(self, results: list):
        template = self.env.get_template(TEMPLATE_NAME)

        stats = {"ok": 0, "warning": 0, "critical": 0}
        cat_stats = {"domain": 0, "ssl": 0, "security": 0, "blacklist": 0}

        for r in results:
            s = r.get("status", "ok")
            if s == "error":
                s = "critical"

            if s in stats:
                stats[s] += 1
            else:
                stats["critical"] += 1

            # Category counters track problems only
            if s != "ok":
                monitor = r.get("monitor", "unknown").lower()
                if monitor in cat_stats:
                    cat_stats[monitor] += 1

        now_utc = datetime.now(timezone.utc)
        html_content = template.render(
            results=results,
            timestamp=now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            timestamp_iso=now_utc.isoformat(),  # ISO 8601 for the staleness check
            stats=stats,
            cat_stats=cat_stats
        )

        output_file = os.path.join(self.output_dir, "index.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        json_file = os.path.join(self.output_dir, "report.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        snapshot = self._write_snapshot(results, now_utc)
        # The run that is happening now is never what retention is about.
        self.prune_history(now_utc, keep={snapshot})

        return output_file

    # ── History ───────────────────────────────────────────────────────────────

    def _write_snapshot(self, results: list, when: datetime) -> str:
        """
        Keep one JSON file per run. Only the JSON is kept, not the HTML: it is
        the machine-readable record a trend would be built from, it is an
        order of magnitude smaller, and index.html can be rendered from it.
        """
        name = f"{HISTORY_PREFIX}{when.strftime(HISTORY_STAMP)}.json"
        path = os.path.join(self.output_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        return path

    def prune_history(self, now: datetime = None, keep: set = None) -> list:
        """
        Delete snapshots older than ``retention_days`` and return what went.

        Returns early when retention is unset, so the default is to keep
        everything rather than silently start deleting a user's history.
        Paths in ``keep`` are never removed.
        """
        if self.retention_days is None:
            return []
        if not isinstance(self.retention_days, int) or self.retention_days < 0:
            logger.warning(
                f"reports.retention_days must be a non-negative whole number, "
                f"got {self.retention_days!r}; keeping every snapshot"
            )
            return []

        now = now or datetime.now(timezone.utc)
        # Snapshot names carry whole seconds, so the cutoff has to as well:
        # otherwise the microseconds on `now` make a file stamped this very
        # second look older than the cutoff.
        cutoff = now.replace(microsecond=0) - timedelta(days=self.retention_days)
        protected = {os.path.abspath(p) for p in (keep or set())}
        removed = []

        for path in glob.glob(os.path.join(self.output_dir, f"{HISTORY_PREFIX}*.json")):
            if os.path.abspath(path) in protected:
                continue
            match = _HISTORY_RE.match(os.path.basename(path))
            if not match:
                continue  # not one of ours; leave it alone
            try:
                stamped = datetime.strptime(match.group(1), HISTORY_STAMP).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            if stamped < cutoff:
                try:
                    os.remove(path)
                    removed.append(path)
                except OSError as e:
                    logger.warning(f"Could not remove old snapshot {path}: {e}")

        if removed:
            logger.info(
                f"Removed {len(removed)} snapshot(s) older than "
                f"{self.retention_days} day(s)"
            )
        return removed
