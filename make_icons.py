#!/usr/bin/env python3
"""PWA 아이콘(192·512) 생성 — 어두운 배경 + 상승 캔들 + 이동평균선. 사용: python3 make_icons.py"""
from pathlib import Path
from PIL import Image, ImageDraw

def icon(n):
    s = 4 * n  # 4배로 그려 축소(안티에일리어싱)
    im = Image.new("RGB", (s, s), "#1a1a19"); d = ImageDraw.Draw(im)
    u = s / 16
    bars = [(4, 9, 11, "#3987e5"), (6.5, 7, 10, "#e66767"), (9, 5.5, 9, "#e66767"), (11.5, 4, 7.5, "#e66767")]
    for x, top, bot, c in bars:  # 안전영역(가운데 80%) 안에 배치 → maskable 겸용
        d.line([(x * u, (top - 0.8) * u), (x * u, (bot + 0.8) * u)], fill=c, width=int(u * 0.25))
        d.rounded_rectangle([(x - 0.7) * u, top * u, (x + 0.7) * u, bot * u], radius=u * 0.2, fill=c)
    d.line([(3 * u, 11.5 * u), (6.5 * u, 9.5 * u), (9 * u, 8 * u), (13 * u, 5 * u)], fill="#eda100", width=int(u * 0.45), joint="curve")
    return im.resize((n, n), Image.LANCZOS)

out = Path(__file__).with_name("site")
for n in (192, 512): icon(n).save(out / f"icon-{n}.png")
print("아이콘 저장:", out)
