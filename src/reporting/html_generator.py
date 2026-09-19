import json
import os
import shutil
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

TEMPLATE_NAME = "report.html"

#: The template shipped with the package. It is a real file rather than a
#: string literal so it can be reviewed in a diff and edited in place.
PACKAGED_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")


class HTMLGenerator:
    def __init__(self, template_dir: str = None, output_dir: str = "reports"):
        self.output_dir = output_dir
        self.template_dir = template_dir or PACKAGED_TEMPLATE_DIR
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

        return output_file
