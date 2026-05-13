"""
領富 AI · PWA 圖示產生器
產出純 stdlib（不需要 PIL）的 PNG 圖示。

設計：墨綠底 + 中央金色圓點（呼應品牌「領富 AI」墨綠金配色）
產出：
  icons/icon-192.png   (Android Chrome)
  icons/icon-512.png   (manifest 主圖)
  icons/icon-maskable-512.png  (Android adaptive icon，內容置中安全區)
  icons/icon-180.png   (iOS apple-touch-icon)
"""

import sys
import struct
import zlib
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "icons"
ICON_DIR.mkdir(exist_ok=True)

# 品牌色
GREEN     = (0x1B, 0x43, 0x32)   # 墓綠主色
GREEN_DK  = (0x0A, 0x1F, 0x18)   # 最深墨綠
GREEN_LT  = (0x2D, 0x6A, 0x4F)   # 中綠
GOLD      = (0xC5, 0xA5, 0x72)   # 暖金
GOLD_LT   = (0xD4, 0xB8, 0x84)   # 亮金


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def color_at(x, y, w, h, maskable=False):
    """決定 (x, y) 的顏色。maskable=True 時 safe zone 是 center 80%。"""
    # 對角線漸層底（左上 GREEN_DK → 右下 GREEN）
    t = (x / w + y / h) / 2
    base = lerp(GREEN_DK, GREEN, t)

    # 中央 AI 主視覺：金色圓
    cx, cy = w / 2, h / 2
    if maskable:
        # safe zone 是 center 80%，圖示置中縮小一點
        radius = w * 0.18
    else:
        radius = w * 0.22

    dx, dy = x - cx, y - cy
    dist = (dx * dx + dy * dy) ** 0.5

    # 金圓 + 細外環
    if dist < radius:
        # 圓內漸層
        gt = dist / radius
        return lerp(GOLD_LT, GOLD, gt)
    if dist < radius + max(3, w * 0.012):
        # 外環
        return GOLD_LT
    return base


def write_png(path, width, height, maskable=False):
    """逐 pixel 計算並輸出 PNG（RGB 8-bit）。"""
    rows = []
    for y in range(height):
        row = bytearray()
        row.append(0)  # filter type: None
        for x in range(width):
            r, g, b = color_at(x, y, width, height, maskable)
            row.append(r)
            row.append(g)
            row.append(b)
        rows.append(bytes(row))
    raw = b"".join(rows)
    compressed = zlib.compress(raw, level=6)

    def chunk(name, data):
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8bit RGB
    png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", compressed) + chunk(b"IEND", b"")
    path.write_bytes(png)
    print(f"  ✅ {path.relative_to(ROOT)}  ({len(png)/1024:.1f} KB)")


def write_svg(path):
    """同樣設計但向量化，作為 favicon 與 manifest 補充。"""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0A1F18"/>
      <stop offset="100%" stop-color="#1B4332"/>
    </linearGradient>
    <radialGradient id="gold" cx="50%" cy="50%">
      <stop offset="0%" stop-color="#D4B884"/>
      <stop offset="100%" stop-color="#C5A572"/>
    </radialGradient>
  </defs>
  <rect width="512" height="512" rx="80" fill="url(#bg)"/>
  <circle cx="256" cy="256" r="118" fill="url(#gold)"/>
  <text x="256" y="296" font-family="'Microsoft JhengHei','PingFang TC',sans-serif"
        font-size="120" font-weight="800" fill="#0A1F18" text-anchor="middle">領</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    print(f"  ✅ {path.relative_to(ROOT)}  (SVG)")


def main():
    print("產出 PWA 圖示...")
    write_png(ICON_DIR / "icon-192.png", 192, 192)
    write_png(ICON_DIR / "icon-512.png", 512, 512)
    write_png(ICON_DIR / "icon-maskable-512.png", 512, 512, maskable=True)
    write_png(ICON_DIR / "icon-180.png", 180, 180)
    write_svg(ICON_DIR / "icon.svg")
    print("✅ 全部完成")


if __name__ == "__main__":
    main()
