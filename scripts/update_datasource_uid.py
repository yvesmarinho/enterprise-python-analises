#!/usr/bin/env python3
"""
Update datasource UID in dashboards to match server configuration.
Changes 'prometheus' to 'victoriametrics' to match wfdb01 setup.
"""

import json
import sys
from pathlib import Path


def update_datasource_uid(file_path: Path, old_uid: str = "prometheus", new_uid: str = "victoriametrics"):
    """Update datasource UID in a dashboard JSON file."""

    print(f"Processing: {file_path.name}")

    with open(file_path, 'r', encoding='utf-8') as f:
        dashboard = json.load(f)

    changes = 0

    # Update panels
    if "panels" in dashboard:
        for panel in dashboard["panels"]:
            # Handle direct datasource
            if isinstance(panel.get("datasource"), dict):
                if panel["datasource"].get("uid") == old_uid:
                    panel["datasource"]["uid"] = new_uid
                    changes += 1
                    print(f"  ✓ Updated panel: {panel.get('title', 'Untitled')}")

            # Handle row panels with nested panels
            if panel.get("type") == "row" and "panels" in panel:
                for subpanel in panel["panels"]:
                    if isinstance(subpanel.get("datasource"), dict):
                        if subpanel["datasource"].get("uid") == old_uid:
                            subpanel["datasource"]["uid"] = new_uid
                            changes += 1
                            print(f"  ✓ Updated subpanel: {subpanel.get('title', 'Untitled')}")

            # Handle targets
            if "targets" in panel:
                for target in panel["targets"]:
                    if isinstance(target.get("datasource"), dict):
                        if target["datasource"].get("uid") == old_uid:
                            target["datasource"]["uid"] = new_uid
                            changes += 1

    # Update templating variables
    if "templating" in dashboard and "list" in dashboard["templating"]:
        for var in dashboard["templating"]["list"]:
            if isinstance(var.get("datasource"), dict):
                if var["datasource"].get("uid") == old_uid:
                    var["datasource"]["uid"] = new_uid
                    changes += 1
                    print(f"  ✓ Updated variable: {var.get('name', 'unnamed')}")

    if changes > 0:
        # Save updated dashboard
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard, f, indent=2, ensure_ascii=False)

        print(f"  📝 Saved {changes} changes")
        return changes
    else:
        print(f"  ℹ️  No changes needed")
        return 0

def main():
    # Target N8N dashboards
    dashboards_dir = Path(__file__).parent.parent / "n8n-prometheus-wfdb01" / "grafana" / "dashboards"

    n8n_dashboards = [
        "n8n-performance-overview.json",
        "n8n-performance-detailed.json",
        "n8n-node-performance.json"
    ]

    total_changes = 0

    print("=" * 60)
    print("Updating Datasource UID: prometheus → victoriametrics")
    print("=" * 60)
    print()

    for dashboard_name in n8n_dashboards:
        file_path = dashboards_dir / dashboard_name

        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        changes = update_datasource_uid(file_path)
        total_changes += changes
        print()

    print("=" * 60)
    print(f"✅ Total changes: {total_changes}")
    print("=" * 60)

    return 0 if total_changes > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
