#!/usr/bin/env python3
"""
X Radar · 小红书图组在线预览页生成器

把 data/xhs/<date>/ 里渲染好的 PNG 拼成一个自包含 HTML（图片 base64 内嵌），
模拟小红书手机版式横向排布，方便用 vibeshare 部署成链接在手机/电脑上审版式。

用法：
    python3 scripts/preview_xhs.py [--date YYYY-MM-DD]
输出：
    data/xhs/<date>/preview.html   （单文件，可直接 vibeshare 部署）
"""
import argparse
import base64
import io
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XHS_DIR = ROOT / "data" / "xhs"

# 预览内嵌图缩小到这个宽度 + JPEG 压缩，避免单 HTML 过大（vibeshare 有体积上限）
PREVIEW_W = 600
JPEG_Q = 78


def img_b64(p: Path) -> str:
    """缩小成 JPEG 再 base64，单文件体积砍约 10x（预览看版式足够清晰）。"""
    try:
        from PIL import Image
        im = Image.open(p).convert("RGB")
        if im.width > PREVIEW_W:
            h = round(im.height * PREVIEW_W / im.width)
            im = im.resize((PREVIEW_W, h), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=JPEG_Q, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        # 没有 PIL 就退回原始 PNG
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def build(date_str: str) -> Path:
    out_dir = XHS_DIR / date_str
    pngs = sorted(out_dir.glob("*.png"))
    if not pngs:
        raise SystemExit(f"没有图：{out_dir}（先跑 render_xhs.py）")

    caption = ""
    cap_path = out_dir / "caption.txt"
    if cap_path.exists():
        caption = cap_path.read_text().strip()

    cards_html = []
    for p in pngs:
        uri = img_b64(p)
        label = p.stem
        cards_html.append(
            f'<figure class="card"><img src="{uri}" alt="{label}">'
            f'<figcaption>{label}</figcaption></figure>'
        )

    md = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m.%d")
    cap_block = ""
    if caption:
        cap_block = f'<section class="cap"><h3>小红书文案</h3><pre>{caption}</pre></section>'

    doc = f"""<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>雷码工坊 · {md} AI 信号图组预览</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#15181E; color:#E6E8EC; font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
          padding:28px 16px 60px; -webkit-font-smoothing:antialiased; }}
  header {{ max-width:1100px; margin:0 auto 22px; display:flex; align-items:baseline; gap:12px; }}
  header .dot {{ width:12px; height:12px; border-radius:50%; background:#1AB87C; display:inline-block; }}
  header h1 {{ font-size:20px; font-weight:800; }}
  header .date {{ color:#9CB4CC; font-size:15px; margin-left:auto; font-family:Menlo,monospace; }}
  .deck {{ max-width:1100px; margin:0 auto; display:flex; gap:18px; overflow-x:auto; padding-bottom:14px;
           scroll-snap-type:x mandatory; }}
  .card {{ flex:0 0 auto; scroll-snap-align:center; }}
  .card img {{ width:270px; height:360px; border-radius:14px; display:block;
               box-shadow:0 8px 30px rgba(0,0,0,.45); }}
  .card figcaption {{ text-align:center; margin-top:8px; font-size:12px; color:#7A828E; font-family:Menlo,monospace; }}
  .hint {{ max-width:1100px; margin:10px auto 0; font-size:13px; color:#7A828E; }}
  .grid {{ max-width:1100px; margin:30px auto 0; display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
           gap:20px; }}
  .grid img {{ width:100%; border-radius:12px; box-shadow:0 6px 20px rgba(0,0,0,.4); }}
  .cap {{ max-width:1100px; margin:34px auto 0; background:#1E2229; border:1px solid #2A2F38;
          border-radius:14px; padding:20px 22px; }}
  .cap h3 {{ font-size:14px; color:#1AB87C; margin-bottom:10px; letter-spacing:1px; }}
  .cap pre {{ white-space:pre-wrap; font-size:14px; line-height:1.7; color:#C9CDD6; font-family:inherit; }}
  h2.sec {{ max-width:1100px; margin:34px auto 14px; font-size:15px; color:#9CB4CC; font-weight:700; }}
</style></head><body>
<header><span class="dot"></span><h1>雷码工坊 · 今日 AI 信号图组</h1><span class="date">{date_str}</span></header>
<h2 class="sec">① 滑动看（小红书横滑顺序）</h2>
<div class="deck">{''.join(cards_html)}</div>
<p class="hint">← 横向滑动 · 顺序即发布顺序（封面 → 内容 → 尾卡）。每张 3:4 / 1080×1440。</p>
<h2 class="sec">② 平铺全看</h2>
<div class="grid">{''.join(f'<img src="{img_b64(p)}" alt="{p.stem}">' for p in pngs)}</div>
{cap_block}
</body></html>"""

    out = out_dir / "preview.html"
    out.write_text(doc)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = ap.parse_args()
    out = build(args.date)
    size_kb = out.stat().st_size // 1024
    print(f"✅ 预览页 → {out}  ({size_kb} KB)")


if __name__ == "__main__":
    main()
