#!/usr/bin/env python3
"""Generate an Excalidraw diagram for PyTorch in-tree CI architecture."""

import json

COMMON = {
    "version": 1,
    "versionNonce": 0,
    "isDeleted": False,
    "fillStyle": "solid",
    "strokeWidth": 2,
    "strokeStyle": "solid",
    "roughness": 0,
    "opacity": 100,
    "angle": 0,
    "seed": 1,
    "groupIds": [],
    "frameId": None,
    "roundness": None,
    "boundElements": [],
    "updated": 1,
    "link": None,
    "locked": False,
}

TEXT_COMMON = {
    **COMMON,
    "strokeWidth": 1,
    "backgroundColor": "transparent",
    "fontFamily": 2,
    "textAlign": "center",
    "verticalAlign": "top",
    "containerId": None,
    "lineHeight": 1.25,
}

nonce = [10]
def nn():
    nonce[0] += 1
    return nonce[0]

def rect(id, x, y, w, h, stroke, bg, style="solid", rnd=3, group=None, sw=2):
    return {
        **COMMON,
        "type": "rectangle",
        "id": id,
        "versionNonce": nn(),
        "x": x, "y": y,
        "width": w, "height": h,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "strokeStyle": style,
        "strokeWidth": sw,
        "roundness": {"type": rnd} if rnd else None,
        "groupIds": [group] if group else [],
    }

def text(id, x, y, w, h, content, stroke, size=16, align="center", group=None):
    return {
        **TEXT_COMMON,
        "type": "text",
        "id": id,
        "versionNonce": nn(),
        "x": x, "y": y,
        "width": w, "height": h,
        "strokeColor": stroke,
        "fontSize": size,
        "text": content,
        "originalText": content,
        "textAlign": align,
        "groupIds": [group] if group else [],
    }

def arrow(id, x1, y1, x2, y2, stroke, style="solid", etype="arrow"):
    points = [[0, 0], [x2 - x1, y2 - y1]]
    return {
        **COMMON,
        "type": "arrow",
        "id": id,
        "versionNonce": nn(),
        "x": x1, "y": y1,
        "width": abs(x2 - x1) or 1,
        "height": abs(y2 - y1) or 1,
        "strokeColor": stroke,
        "backgroundColor": "transparent",
        "strokeStyle": style,
        "roundness": {"type": 2},
        "points": points,
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": etype,
    }

def line(id, x1, y1, x2, y2, stroke, style="solid", group=None):
    return {
        **COMMON,
        "type": "line",
        "id": id,
        "versionNonce": nn(),
        "x": x1, "y": y1,
        "width": abs(x2 - x1) or 1,
        "height": abs(y2 - y1) or 1,
        "strokeColor": stroke,
        "backgroundColor": "transparent",
        "strokeStyle": style,
        "roundness": {"type": 2},
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "lastCommittedPoint": None,
        "startBinding": None,
        "endBinding": None,
        "startArrowhead": None,
        "endArrowhead": None,
        "groupIds": [group] if group else [],
    }

def ellipse(id, x, y, w, h, stroke, bg, group=None):
    return {
        **COMMON,
        "type": "ellipse",
        "id": id,
        "versionNonce": nn(),
        "x": x, "y": y,
        "width": w, "height": h,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "roundness": {"type": 2},
        "groupIds": [group] if group else [],
    }

def cylinder(prefix, x, y, w, h, stroke, bg, group_id):
    """Database cylinder: bottom ellipse, body, left/right walls, top ellipse + text area."""
    eh = 22
    return [
        ellipse(f"{prefix}-bot-ellipse", x, y + h - eh, w, eh, stroke, bg, group_id),
        {
            **COMMON,
            "type": "rectangle",
            "id": f"{prefix}-body",
            "versionNonce": nn(),
            "x": x, "y": y + eh // 2,
            "width": w, "height": h - eh,
            "strokeColor": "transparent",
            "backgroundColor": bg,
            "roundness": None,
            "groupIds": [group_id],
        },
        line(f"{prefix}-left-wall", x, y + eh // 2, x, y + h - eh // 2, stroke, group=group_id),
        line(f"{prefix}-right-wall", x + w, y + eh // 2, x + w, y + h - eh // 2, stroke, group=group_id),
        ellipse(f"{prefix}-top-ellipse", x, y, w, eh, stroke, bg, group_id),
    ]

# ─── Color palette ───
BLUE_S = "#1971c2"
BLUE_B = "#a5d8ff"
BLUE_LIGHT = "#d0ebff"
ORANGE_S = "#e8590c"
ORANGE_B = "#fff4e6"
GREEN_S = "#2f9e44"
GREEN_B = "#b2f2bb"
RED_S = "#e03131"
RED_B = "#ffc9c9"
YELLOW_S = "#e67700"
YELLOW_B = "#fff3bf"
GRAY = "#495057"
DARK = "#1e1e1e"

elements = []

# ═══════════════════════════════════════════
# SECTION: PyTorch Infrastructure dashed border
# ═══════════════════════════════════════════
elements.append(rect("infra-border", 240, 25, 600, 660, BLUE_S, "transparent", style="dashed"))
elements.append(text("infra-title", 370, 35, 340, 30, "PyTorch Infrastructure", BLUE_S, 22))

# ═══════════════════════════════════════════
# SECTION: Upstream
# ═══════════════════════════════════════════
elements.append(text("upstream-title", 45, 95, 130, 25, "Upstream", ORANGE_S, 20))

elements.append(rect("upstream-box", 20, 125, 190, 120, ORANGE_S, ORANGE_B))
elements.append(text("upstream-repo", 35, 138, 160, 22, "pytorch/pytorch", DARK, 17))
elements.append(text("upstream-detail", 35, 168, 160, 50,
    "PR is opened,\nupdated, or merged", GRAY, 14))

# ═══════════════════════════════════════════
# COMPONENT: GitHub Actions
# ═══════════════════════════════════════════
elements.append(rect("gha-box", 270, 80, 240, 110, BLUE_S, BLUE_B))
elements.append(text("gha-title", 290, 88, 200, 22, "GitHub Actions", DARK, 17))
elements.append(text("gha-desc", 285, 115, 210, 65,
    "· .github/workflows/\n· ciflow label gating\n· Job matrix generation\n· Workflow orchestration", GRAY, 13))

# ═══════════════════════════════════════════
# COMPONENT: Self-hosted Runner Fleet
# ═══════════════════════════════════════════
elements.append(rect("runner-box", 270, 240, 240, 120, BLUE_S, BLUE_B))
elements.append(text("runner-title", 285, 248, 210, 22, "Self-hosted Runner Fleet", DARK, 16))
elements.append(text("runner-desc", 285, 276, 210, 70,
    "· AWS EC2 (Linux, Windows)\n· GPU instances (CUDA, ROCm)\n· Managed by test-infra\n· Build + test execution", GRAY, 13))

# ═══════════════════════════════════════════
# COMPONENT: S3 (cylinder)
# ═══════════════════════════════════════════
s3_x, s3_y = 270, 420
s3_w, s3_h = 140, 80
elements.extend(cylinder("s3", s3_x, s3_y, s3_w, s3_h, YELLOW_S, YELLOW_B, "s3-cyl"))
elements.append(text("s3-label", s3_x + 15, s3_y + 22, 110, 45,
    "S3\nTest XML reports\nBuild artifacts", DARK, 12, group="s3-cyl"))

# ═══════════════════════════════════════════
# COMPONENT: Data Pipeline / Ingestion
# ═══════════════════════════════════════════
elements.append(rect("pipeline-box", 460, 420, 170, 80, BLUE_S, BLUE_LIGHT))
elements.append(text("pipeline-title", 475, 428, 140, 22, "Data Pipeline", DARK, 16))
elements.append(text("pipeline-desc", 475, 454, 140, 35,
    "test-infra ingestion\nXML → structured data", GRAY, 12))

# ═══════════════════════════════════════════
# COMPONENT: ClickHouse (cylinder)
# ═══════════════════════════════════════════
ch_x, ch_y = 460, 560
ch_w, ch_h = 170, 90
elements.extend(cylinder("ch", ch_x, ch_y, ch_w, ch_h, YELLOW_S, YELLOW_B, "ch-cyl"))
elements.append(text("ch-label", ch_x + 15, ch_y + 22, 140, 50,
    "ClickHouse\ndefault.workflow_job\ndefault.test_run_s3", DARK, 12, group="ch-cyl"))

# ═══════════════════════════════════════════
# RIGHT SIDE: GitHub PR Checks
# ═══════════════════════════════════════════
elements.append(text("viz-title-top", 880, 90, 200, 22, "Developer View", GREEN_S, 18))

elements.append(rect("checks-box", 870, 120, 200, 100, GREEN_S, GREEN_B))
elements.append(text("checks-title", 885, 128, 170, 22, "GitHub PR Checks", DARK, 16))
elements.append(text("checks-desc", 885, 155, 170, 50,
    "· Native check runs\n· Pass/fail on PR page\n· Required status checks", GRAY, 13))

# ═══════════════════════════════════════════
# RIGHT SIDE: Merge Queue
# ═══════════════════════════════════════════
elements.append(rect("merge-box", 870, 260, 200, 80, GREEN_S, GREEN_B))
elements.append(text("merge-title", 885, 270, 170, 22, "Merge Queue", DARK, 16))
elements.append(text("merge-desc", 885, 294, 170, 35,
    "· GitHub merge queue\n· Trunk validation", GRAY, 13))

# ═══════════════════════════════════════════
# RIGHT SIDE: PyTorch CI HUD
# ═══════════════════════════════════════════
elements.append(text("viz-title-bot", 880, 400, 200, 22, "User Visualization", RED_S, 18))

elements.append(rect("hud-box", 870, 430, 200, 110, RED_S, RED_B))
elements.append(text("hud-title", 885, 438, 170, 22, "PyTorch CI HUD", DARK, 16))
elements.append(text("hud-desc", 885, 465, 170, 60,
    "hud.pytorch.org\n· Test dashboards\n· Failure analysis\n· Flaky test tracking", GRAY, 13))

# ═══════════════════════════════════════════
# ARROWS
# ═══════════════════════════════════════════

# 1. Upstream → GitHub Actions (PR event)
elements.append(arrow("a1", 210, 175, 270, 135, GRAY))
elements.append(text("a1-lbl", 210, 135, 70, 18, "PR event", GRAY, 11))

# 2. GitHub Actions → Runner Fleet (dispatch jobs)
elements.append(arrow("a2", 390, 190, 390, 240, GRAY))
elements.append(text("a2-lbl", 398, 205, 100, 18, "dispatches jobs", GRAY, 11))

# 3. Runner Fleet → GitHub PR Checks (check run updates)
elements.append(arrow("a3", 510, 280, 870, 165, GRAY))
elements.append(text("a3-lbl", 610, 200, 170, 18, "check run status updates", GRAY, 11))

# 4. Runner Fleet → Merge Queue (status gates merge)
elements.append(arrow("a4", 510, 310, 870, 300, GRAY, style="dashed"))
elements.append(text("a4-lbl", 620, 280, 130, 18, "status gates merge", GRAY, 11))

# 5. Runner Fleet → S3 (upload test XMLs)
elements.append(arrow("a5", 340, 360, 340, 420, GRAY))
elements.append(text("a5-lbl", 348, 375, 90, 18, "upload XMLs", GRAY, 11))

# 6. S3 → Data Pipeline
elements.append(arrow("a6", 410, 460, 460, 460, GRAY))

# 7. Data Pipeline → ClickHouse (ingest)
elements.append(arrow("a7", 545, 500, 545, 560, GRAY))
elements.append(text("a7-lbl", 552, 520, 50, 18, "ingest", GRAY, 11))

# 8. ClickHouse → HUD (query results)
elements.append(arrow("a8", 630, 600, 870, 490, GRAY))
elements.append(text("a8-lbl", 700, 530, 90, 18, "query results", GRAY, 11))

# ═══════════════════════════════════════════
# LEGEND (bottom-left)
# ═══════════════════════════════════════════
lx, ly = 20, 530
elements.append(rect("legend-border", lx, ly, 200, 155, GRAY, "#f8f9fa", sw=1))
elements.append(text("legend-title", lx + 10, ly + 6, 80, 20, "Legend", DARK, 15))

legend_items = [
    (BLUE_S, BLUE_B, "PyTorch compute"),
    (YELLOW_S, YELLOW_B, "Data store"),
    (GREEN_S, GREEN_B, "GitHub-native"),
    (RED_S, RED_B, "CI HUD dashboard"),
]
for i, (sc, bg, label) in enumerate(legend_items):
    iy = ly + 32 + i * 28
    elements.append(rect(f"leg-sq-{i}", lx + 12, iy, 18, 18, sc, bg, rnd=0))
    elements.append(text(f"leg-lbl-{i}", lx + 38, iy, 145, 18, label, DARK, 13, align="left"))

# Arrow legend
aly = ly + 32 + len(legend_items) * 28
elements.append(arrow(f"leg-arr-solid", lx + 12, aly + 8, lx + 28, aly + 8, GRAY))
elements.append(text(f"leg-arr-solid-lbl", lx + 38, aly, 145, 18, "Data / control flow", DARK, 13, align="left"))

# ═══════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════
elements.append(text("diagram-title", 300, -5, 500, 30,
    "PyTorch In-Tree CI Architecture", DARK, 11))

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": "#ffffff"
    },
    "files": {}
}

out = "/home/sugeorge/Documents/PR-related-files/pytorch/agent_space/intree_ci_architecture_diagram.excalidraw"
with open(out, "w") as f:
    json.dump(doc, f, indent=2)

print(f"Written {len(elements)} elements to {out}")
