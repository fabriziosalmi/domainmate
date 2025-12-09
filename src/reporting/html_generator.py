import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, timedelta, timezone
import json

class HTMLGenerator:
    def __init__(self, template_dir: str = "src/templates", output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(template_dir, exist_ok=True)
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self._create_default_template(os.path.join(template_dir, "report.html"))

    def _create_default_template(self, path: str):
        with open(path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DomainMate Security Audit</title>
    <!-- Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/rowgroup/1.4.1/css/rowGroup.bootstrap5.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/5.3.0/css/bootstrap.min.css">
    
    <style>
        :root {
            --primary-bg: #f8f9fa;
            --card-bg: #ffffff;
            --text-main: #1f2937;
            --text-secondary: #6b7280;
            --border-color: #e5e7eb;
            --success-bg: #ecfdf5; --success-text: #047857;
            --warning-bg: #fffbeb; --warning-text: #b45309;
            --danger-bg: #fef2f2; --danger-text: #b91c1c;
            --info-bg: #eff6ff; --info-text: #1d4ed8;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--primary-bg);
            color: var(--text-main);
            font-size: 0.875rem;
            padding-bottom: 40px;
        }

        .navbar {
            background-color: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }

        .navbar-brand {
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: -0.025em;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .kpi-card {
            background: var(--card-bg);
            padding: 1.5rem;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        }

        .kpi-label {
            color: var(--text-secondary);
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }

        .kpi-value {
            font-size: 2.25rem;
            font-weight: 700;
            line-height: 1;
        }

        .main-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            padding: 1.5rem;
        }

        .badge-ent {
            padding: 0.25em 0.6em;
            font-size: 0.75em;
            font-weight: 600;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .badge-ok { background-color: var(--success-bg); color: var(--success-text); border: 1px solid rgba(4, 120, 87, 0.1); }
        .badge-warning { background-color: var(--warning-bg); color: var(--warning-text); border: 1px solid rgba(180, 83, 9, 0.1); }
        .badge-critical { background-color: var(--danger-bg); color: var(--danger-text); border: 1px solid rgba(185, 28, 28, 0.1); }
        .badge-error { background-color: var(--danger-bg); color: var(--danger-text); border: 1px solid rgba(185, 28, 28, 0.1); }

        table.dataTable thead th {
            font-weight: 600;
            color: var(--text-secondary);
            background-color: #f9fafb;
            border-bottom: 2px solid var(--border-color);
        }
        
        table.dataTable tbody td {
            vertical-align: middle;
            color: var(--text-main);
        }

        .progress {
            height: 6px;
            background-color: var(--border-color);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 6px;
        }
        .progress-bar { height: 100%; }
        
        .technical-details {
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.75em;
            color: var(--text-secondary);
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            display: inline-block;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* SVG Icons classes */
        .icon { width: 20px; height: 20px; vertical-align: bottom; }
        .icon-sm { width: 16px; height: 16px; margin-right: 4px; vertical-align: text-bottom; }

    </style>
</head>
<body>

    <nav class="navbar">
        <div class="container-fluid max-w-7xl mx-auto">
            <div class="navbar-brand">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                DomainMate
            </div>
            <div class="text-secondary">
                Report Generated: {{ timestamp }}
            </div>
        </div>
    </nav>

    <div class="container-fluid px-4" style="max-width: 1400px; margin: 0 auto;">
        
        <!-- KPI Summary -->
        <div class="kpi-grid">
            <div class="kpi-card" style="border-left: 4px solid var(--success-text);">
                <div class="kpi-label">Compliance Status</div>
                <div class="kpi-value" style="color: var(--success-text);">
                    {% if stats.critical == 0 and stats.warning == 0 %}100%{% else %}{{ ((results|length - stats.critical - stats.warning) / results|length * 100)|round|int }}%{% endif %}
                </div>
                <div class="text-secondary mt-1" style="font-size: 0.8em;">Operational Health</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">Passing Checks</div>
                <div class="kpi-value text-dark">{{ stats.ok }}</div>
                <div class="text-secondary mt-1" style="font-size: 0.8em;">Checks Passed</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">Warnings</div>
                <div class="kpi-value" style="color: var(--warning-text);">{{ stats.warning }}</div>
                <div class="text-secondary mt-1" style="font-size: 0.8em;">Requires Attention</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-label">Critical Issues</div>
                <div class="kpi-value" style="color: var(--danger-text);">{{ stats.critical }}</div>
                <div class="text-secondary mt-1" style="font-size: 0.8em;">Immediate Action Required</div>
            </div>
        </div>

        <!-- Category Issues Breakdown -->
        <h6 class="text-secondary mb-3 text-uppercase font-weight-bold" style="font-size: 0.75rem; letter-spacing: 0.05em;">Issues by Category</h6>
        <div class="kpi-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
            <!-- Domain Card -->
            <div class="kpi-card p-3">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="kpi-label mb-1">Domain Issues</div>
                        <div class="text-secondary" style="font-size: 0.75em;">Expiry / WHOIS</div>
                    </div>
                    <div class="kpi-value" style="{{ 'color: var(--danger-text);' if cat_stats.domain > 0 else 'color: var(--text-secondary); opacity: 0.5;' }} font-size: 1.75rem;">
                        {{ cat_stats.domain }}
                    </div>
                </div>
            </div>

            <!-- SSL Card -->
            <div class="kpi-card p-3">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="kpi-label mb-1">SSL Issues</div>
                        <div class="text-secondary" style="font-size: 0.75em;">Cert / Chains</div>
                    </div>
                    <div class="kpi-value" style="{{ 'color: var(--danger-text);' if cat_stats.ssl > 0 else 'color: var(--text-secondary); opacity: 0.5;' }} font-size: 1.75rem;">
                        {{ cat_stats.ssl }}
                    </div>
                </div>
            </div>

            <!-- Security Card -->
            <div class="kpi-card p-3">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="kpi-label mb-1">Security Issues</div>
                        <div class="text-secondary" style="font-size: 0.75em;">Headers / Protocols</div>
                    </div>
                    <div class="kpi-value" style="{{ 'color: var(--danger-text);' if cat_stats.security > 0 else 'color: var(--text-secondary); opacity: 0.5;' }} font-size: 1.75rem;">
                        {{ cat_stats.security }}
                    </div>
                </div>
            </div>

            <!-- Blacklist Card -->
            <div class="kpi-card p-3">
                <div class="d-flex align-items-center justify-content-between">
                    <div>
                        <div class="kpi-label mb-1">Blacklist Issues</div>
                        <div class="text-secondary" style="font-size: 0.75em;">RBL Listings</div>
                    </div>
                    <div class="kpi-value" style="{{ 'color: var(--danger-text);' if cat_stats.blacklist > 0 else 'color: var(--text-secondary); opacity: 0.5;' }} font-size: 1.75rem;">
                        {{ cat_stats.blacklist }}
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Datatable -->
        <div class="main-card">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h5 class="m-0 font-weight-bold">Detailed Security Ledger</h5>
                <!-- Custom status filter will be injected here by JS if needed, or we use DataTables built-in -->
            </div>

            <table id="auditTable" class="table table-hover" style="width:100%">
                <thead>
                    <tr>
                        <th width="20%">Asset / Domain</th>
                        <th width="10%">Monitor Type</th>
                        <th width="10%">Status</th>
                        <th width="35%">Audit Result</th>
                        <th width="25%">Technical Metadata / Expiry</th>
                    </tr>
                </thead>
                <tbody>
                    {% for result in results %}
                    <tr>
                        <td class="font-weight-600">{{ result.domain }}</td>
                        <td>
                            <span style="font-family: 'SFMono-Regular', monospace; font-size: 0.85em; color: var(--text-secondary); text-transform: uppercase;">{{ result.monitor }}</span>
                        </td>
                        <td>
                            <span class="badge-ent badge-{{ result.status }}">
                                {{ result.status|upper }}
                            </span>
                        </td>
                        <td>
                             <div style="font-weight: 500;">{{ result.message or "Check Passed" }}</div>
                        </td>
                        <td>
                             {% if result.days_until_expiry is defined %}
                                {% set pct = (result.days_until_expiry / 365) * 100 %}
                                {% if pct > 100 %}{% set pct = 100 %}{% endif %}
                                {% set bar_color = '#10b981' %}
                                {% if result.days_until_expiry < 30 %}{% set bar_color = '#f59e0b' %}{% endif %}
                                {% if result.days_until_expiry < 7 %}{% set bar_color = '#ef4444' %}{% endif %}
                                
                                <div class="d-flex align-items-center justify-content-between">
                                    <span class="font-weight-bold" style="font-size: 0.85em;">{{ result.days_until_expiry }} days remaining</span>
                                    <span class="text-muted" style="font-size: 0.75em;">{{ result.expiration_date }}</span>
                                </div>
                                <div class="progress">
                                    <div class="progress-bar" style="width: {{ pct }}%; background-color: {{ bar_color }};"></div>
                                </div>
                            {% elif result.monitor == 'blacklist' %}
                                {% if result.listed_in %}
                                    <span class="technical-details" style="color: var(--danger-text);">{{ result.listed_in | join(', ') }}</span>
                                {% else %}
                                    <span class="text-muted" style="font-size: 0.8em;">Clean IP Reputation</span>
                                {% endif %}
                            {% else %}
                                {% if result.details %}
                                    <span class="technical-details" title="{{ result.details | tojson }}">{{ result.details | tojson | truncate(60) }}</span>
                                {% else %}
                                    <span class="text-muted">–</span>
                                {% endif %}
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.datatables.net/rowgroup/1.4.1/js/dataTables.rowGroup.min.js"></script>
    
    <script>
        $(document).ready(function() {
            var table = $('#auditTable').DataTable({
                "order": [[ 0, "asc" ]], // Order by Domain first for grouping
                "pageLength": 50, // Show more rows per page since we group
                "rowGroup": {
                    "dataSrc": 0,
                    "startRender": function ( rows, group ) {
                        return $('<tr/>')
                            .append( '<td colspan="5" style="background-color: #e5e7eb; font-weight: 700; color: #374151; padding-top: 12px; padding-bottom: 12px;">' + group + ' <span class="badge bg-secondary rounded-pill ms-2" style="font-size: 0.7em;">' + rows.count() + ' Checks</span></td>' );
                    }
                },
                "columnDefs": [
                    { "visible": false, "targets": 0 } // Hide the first column (Domain) since it's in the header
                ],
                "language": {
                    "search": "Filter Records:",
                    "lengthMenu": "Show _MENU_ entries",
                },
                "dom": '<"d-flex justify-content-between mb-3"lf>rt<"d-flex justify-content-between mt-3"ip>'
            });

            // Data Freshness Check
            const reportTimeStr = "{{ timestamp }}"; // format: YYYY-MM-DD HH:MM:SS UTC
            // Parse UTC string manually to satisfy all browsers or leave as string if ISO
            // Python output was "%Y-%m-%d %H:%M:%S UTC". Let's parse strictly.
            // Simplified approach: pass ISO timestamp from python for easier JS parsing.
            
            const generatedAt = new Date("{{ timestamp_iso }}");
            const now = new Date();
            const diffHours = (now - generatedAt) / (1000 * 60 * 60);

            if (diffHours > 25) {
                const banner = `
                <div class="alert alert-danger d-flex align-items-center mb-4" role="alert">
                    <svg class="icon icon-lg me-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <div>
                        <strong>DATA STALE WARNING:</strong> This report was generated more than 24 hours ago (${Math.round(diffHours)}h). The automated scan may have failed.
                    </div>
                </div>`;
                $('.container-fluid.px-4').prepend(banner);
            }
        });
    </script>
</body>
</html>
""")

    def generate(self, results: list):
        template = self.env.get_template("report.html")
        
        # Stats
        stats = {"ok": 0, "warning": 0, "critical": 0}
        cat_stats = {"domain": 0, "ssl": 0, "security": 0, "blacklist": 0}
        
        for r in results:
            s = r.get("status", "ok")
            if s == "error": s = "critical"
            
            # Global Stats
            if s in stats:
                stats[s] += 1
            else:
                stats["critical"] += 1
                
            # Category Stats (Count only if NOT ok)
            if s != "ok":
                monitor = r.get("monitor", "unknown").lower()
                if monitor in cat_stats:
                    cat_stats[monitor] += 1

        html_content = template.render(
            results=results,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            timestamp_iso=datetime.utcnow().isoformat() + "Z", # ISO 8601 for JS
            stats=stats,
            cat_stats=cat_stats
        )
        
        output_file = os.path.join(self.output_dir, "index.html")
        with open(output_file, "w") as f:
            f.write(html_content)
        
        json_file = os.path.join(self.output_dir, f"report.json")
        with open(json_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
            
        return output_file
