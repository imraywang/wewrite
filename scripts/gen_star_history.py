#!/usr/bin/env python3
"""生成自托管的 Star History 图表（docs/star-history.svg）。

为什么自托管：GitHub 新的 API 限制下，star-history.com 等第三方图表服务需要
用户自备 fine-grained PAT 才能拉数据（共享 token 池已 503/429），而 README
嵌入的图片 URL 无法安全携带 token。本脚本改用本仓库 CI 的 GITHUB_TOKEN
（Actions 每次运行临时签发、仅限本仓库）拉 stargazer 时间线，渲染成静态
SVG 提交入库，由 GitHub 直接伺服，永不裂图。

用法：
    GITHUB_TOKEN=$(gh auth token) python3 scripts/gen_star_history.py
    python3 scripts/gen_star_history.py --repo owner/name -o out.svg

CI：.github/workflows/star-history.yml 每周跑一次并自动提交。
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 视觉参数（与 README 徽章色系一致）
W, H = 800, 360
PAD_L, PAD_R, PAD_T, PAD_B = 64, 24, 44, 44
LINE = "#059669"
GRID = "#e5e7eb"
TEXT = "#6b7280"
TITLE = "#374151"


def _ssl_context():
    """macOS 框架版 Python 常缺根证书——有 certifi 就用，否则走系统默认。"""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch_star_dates(repo: str, token: str | None) -> list[date]:
    """拉全部 stargazer 的 starred_at（分页，100/页）。"""
    dates = []
    page = 1
    while True:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/stargazers?per_page=100&page={page}",
            headers={
                "Accept": "application/vnd.github.star+json",
                "User-Agent": "wewrite-star-history",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            })
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as resp:
            batch = json.load(resp)
        if not batch:
            break
        dates.extend(datetime.fromisoformat(s["starred_at"].replace("Z", "+00:00")).date()
                     for s in batch)
        if len(batch) < 100:
            break
        page += 1
    return sorted(dates)


def _nice_ceil(n: int) -> int:
    """y 轴上限取整到「1/2/2.5/5 × 10^k」。"""
    if n <= 10:
        return 10
    from math import log10
    mag = 10 ** int(log10(n))
    for m in (1, 2, 2.5, 5, 10):
        if n <= m * mag:
            return int(m * mag)
    return 10 * mag


def render_svg(dates: list[date], repo: str) -> str:
    today = date.today()
    d0 = dates[0]
    span = max((today - d0).days, 1)
    total = len(dates)
    y_max = _nice_ceil(total)

    def x(d: date) -> float:
        return PAD_L + (d - d0).days / span * (W - PAD_L - PAD_R)

    def y(n: float) -> float:
        return H - PAD_B - n / y_max * (H - PAD_T - PAD_B)

    # 累计曲线点（按天聚合，最多 ~400 点足够平滑）
    pts = []
    count = 0
    last_day = None
    for d in dates:
        count += 1
        if d != last_day:
            pts.append((x(d), y(count)))
            last_day = d
        else:
            pts[-1] = (x(d), y(count))
    pts.append((x(today), y(total)))
    polyline = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{PAD_L},{y(0):.1f} " + polyline + f" {pts[-1][0]:.1f},{y(0):.1f}"

    # 网格与刻度
    rows = []
    for i in range(5):
        n = y_max * i / 4
        yy = y(n)
        rows.append(f'<line x1="{PAD_L}" y1="{yy:.1f}" x2="{W - PAD_R}" y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        label = f"{n/1000:.1f}k".replace(".0k", "k") if n >= 1000 else f"{int(n)}"
        rows.append(f'<text x="{PAD_L - 8}" y="{yy + 4:.1f}" text-anchor="end" font-size="12" fill="{TEXT}">{label}</text>')
    # x 轴 5 个日期刻度
    for i in range(5):
        d = date.fromordinal(d0.toordinal() + span * i // 4)
        xx = x(d)
        anchor = "end" if i == 4 else ("start" if i == 0 else "middle")
        rows.append(f'<text x="{xx:.1f}" y="{H - PAD_B + 18}" text-anchor="{anchor}" font-size="12" fill="{TEXT}">{d.strftime("%Y-%m-%d")}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>text {{ font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}</style>
  <rect width="{W}" height="{H}" fill="white" rx="8"/>
  <text x="{PAD_L}" y="26" font-size="15" font-weight="600" fill="{TITLE}">{repo} · GitHub Stars</text>
  <text x="{W - PAD_R}" y="26" text-anchor="end" font-size="14" font-weight="700" fill="{LINE}">★ {total:,}</text>
  {"".join(rows)}
  <polygon points="{area}" fill="{LINE}" opacity="0.08"/>
  <polyline points="{polyline}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="{LINE}"/>
  <text x="{W - PAD_R}" y="{H - 10}" text-anchor="end" font-size="10" fill="{TEXT}">updated {today.isoformat()}</text>
</svg>
'''


def main() -> None:
    ap = argparse.ArgumentParser(description="生成自托管 star history SVG")
    ap.add_argument("--repo", default="imraywang/wewrite")
    ap.add_argument("-o", "--output", default=str(REPO_ROOT / "docs" / "star-history.svg"))
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    dates = fetch_star_dates(args.repo, token)
    if not dates:
        print("没有 star 数据，跳过生成", file=sys.stderr)
        sys.exit(0)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_svg(dates, args.repo), encoding="utf-8")
    print(f"✓ {out}（{len(dates)} stars，起点 {dates[0]}）")


if __name__ == "__main__":
    main()
