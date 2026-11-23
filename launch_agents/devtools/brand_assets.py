"""Renders the raster brand assets from the one SVG mark (ADR-0041). Owned by T-011.

    bash scripts/py.sh -m launch_agents.devtools.brand_assets

Writes ``frontend/public/favicon-32.png``, ``apple-touch-icon.png`` and ``og-image.png``
(1200 x 630: mark, word mark and tagline). The name and tagline are read from
``frontend/src/brand/brand.ts`` and the mark from ``public/favicon.svg``, so renaming the
product is: change the constants, re-run this script.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

__all__ = ["BrandText", "brand_text", "og_image_html", "render_brand_assets"]

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend"
PRIMARY = "#1b3682"  # --color-primary (light), src/design/tokens.css
MARK_PATHS = (
    "M13 2.5C18.5 7 22.5 12.5 25.5 19.5H13Z",
    "M3 21.5H29L25 27H7Z",
    "M14.25 27H17.75L17 30.5H15Z",
)


class BrandText:
    def __init__(self, name: str, tagline: str) -> None:
        self.name = name
        self.tagline = tagline


def brand_text(brand_ts: Path = FRONTEND / "src" / "brand" / "brand.ts") -> BrandText:
    source = brand_ts.read_text(encoding="utf-8")
    name = re.search(r'BRAND_FALLBACK_NAME\s*=\s*"([^"]+)"', source)
    tagline = re.search(r'TAGLINE\s*=\s*"([^"]+)"', source)
    if not name or not tagline:
        raise ValueError(f"brand constants not found in {brand_ts}")
    return BrandText(name.group(1), tagline.group(1))


def _mark_svg(color: str, size: int) -> str:
    paths = "".join(f'<path d="{d}"/>' for d in MARK_PATHS)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="{size}" height="{size}" fill="{color}">{paths}</svg>'


def _font_face() -> str:
    font = FRONTEND / "node_modules" / "@fontsource-variable" / "inter" / "files" / "inter-latin-wght-normal.woff2"
    if not font.is_file():
        return ""
    data = base64.b64encode(font.read_bytes()).decode("ascii")
    return f"@font-face{{font-family:'Inter';font-weight:100 900;src:url(data:font/woff2;base64,{data}) format('woff2');}}"


def og_image_html(text: BrandText) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{_font_face()}
html,body{{margin:0;width:1200px;height:630px;}}
body{{font-family:Inter,system-ui,sans-serif;background:#f6f8fb;color:#0f172a;display:flex;flex-direction:column;justify-content:center;padding:0 96px;box-sizing:border-box;position:relative;}}
.brand{{display:flex;align-items:center;gap:28px;}}
.word{{font-size:104px;font-weight:650;letter-spacing:-0.035em;}}
.tag{{margin-top:36px;font-size:44px;font-weight:500;line-height:1.2;color:#1b2a4a;max-width:1010px;letter-spacing:-0.01em;}}
.band{{position:absolute;left:0;right:0;bottom:0;height:22px;background:{PRIMARY};}}
</style></head><body>
<div class="brand">{_mark_svg(PRIMARY, 132)}<span class="word">{text.name}</span></div>
<div class="tag">{text.tagline}</div>
<div class="band"></div>
</body></html>"""


def _tile_html(size: int) -> str:
    favicon = (FRONTEND / "public" / "favicon.svg").read_text(encoding="utf-8")
    favicon = re.sub(r'width="32" height="32"', f'width="{size}" height="{size}"', favicon, count=1)
    return f"<!doctype html><html><head><style>html,body{{margin:0;background:transparent}}svg{{display:block}}</style></head><body>{favicon}</body></html>"


def render_brand_assets(out_dir: Path = FRONTEND / "public") -> list[Path]:
    from playwright.sync_api import sync_playwright

    text = brand_text()
    written: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for name, size in (("favicon-32.png", 32), ("apple-touch-icon.png", 180)):
                page = browser.new_page(viewport={"width": size, "height": size})
                page.set_content(_tile_html(size))
                path = out_dir / name
                page.screenshot(path=str(path), omit_background=True)
                page.close()
                written.append(path)
            page = browser.new_page(viewport={"width": 1200, "height": 630})
            page.set_content(og_image_html(text))
            page.wait_for_timeout(200)
            path = out_dir / "og-image.png"
            page.screenshot(path=str(path))
            page.close()
            written.append(path)
        finally:
            browser.close()
    return written


if __name__ == "__main__":  # pragma: no cover
    for written_path in render_brand_assets():
        print(f"wrote {written_path.relative_to(REPO_ROOT)}")
