#!/usr/bin/env python3
"""
X Radar · 小红书 AI 日更卡片组生成器（M4）

输入：一份选好题的 JSON（见下方 schema），由选题分析阶段产出。
输出：一组 3:4 PNG 卡片到 data/xhs/<date>/，每图一条新闻（3240×4320，device_scale_factor=6）。
- 内容卡 ×N（「信号卡」范式：墨黑标题 + 石墨事实 + 磷绿竖线引出「雷码视角」；首图即封面）
- 尾卡 CTA 已移除（含「关注」字样，小红书跨平台易被拦截/降权）；render_cta() 保留备查不再调用

品牌色（雷码工坊 v2 终端磷绿）：
- 墨黑 #0E1116  大标题 / 结构
- 磷绿 #1AB87C  强调 / 信号点 / CTA
- 米白 #FAF7F0  背景
- 石墨 #3A4151  正文（替代纯黑）
- 雾蓝 #9CB4CC  次要 / 角标
- 砖灰 #6E6259  辅助

用法：
    python3 scripts/render_xhs.py [--input data/xhs/<date>.json] [--date YYYY-MM-DD]
    python3 scripts/render_xhs.py --sample        # 用内置样例数据跑通最小闭环

JSON schema（选题分析阶段产出）：
{
  "date": "2026-06-28",
  "hook": "今日 5 条 AI 信号 · 3 分钟看懂",      # 封面钩子（可选，缺省自动拼）
  "cards": [
    {
      "category": "模型发布",                     # 分类标签
      "title": "Claude Opus 4.8 上线百万上下文",  # 钩子标题（产品名保留英文）
      "fact": "Anthropic 发布 Opus 4.8，...",     # 核心事实 2-3 句
      "take": "对做长文档/代码库的人来说，...",    # 雷码视角点评 1 段
      "source": "@AnthropicAI"                    # 出处
    }
  ],
  "caption": "...",                               # 小红书正文文案（可选）
  "tags": ["#AI", "#智能体"]                       # 固定 tag 组（可选）
}
"""
import os
import sys
import json
import html as htmllib
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XHS_DIR = ROOT / "data" / "xhs"

# ---------- 品牌色 ----------
INK = "#0E1116"      # 墨黑
PHOS = "#1AB87C"     # 磷绿
CREAM = "#FAF7F0"    # 米白
GRAPHITE = "#3A4151" # 石墨
MIST = "#9CB4CC"     # 雾蓝
BRICK = "#6E6259"    # 砖灰


def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def esc(s: str) -> str:
    return htmllib.escape((s or "").strip())


# ---------- 共享 CSS ----------
# 卡片 = 540×720 CSS px，截图时 device_scale_factor=SCALE → 高分辨率 3:4
# SCALE=6 → 3240×4320（2026-07-02 应 Andy 要求从 3x 翻倍，App 重压后仍清晰）
CARD_W, CARD_H = 540, 720
SCALE = 6

BASE_CSS = f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{CARD_W}px; height:{CARD_H}px; }}
body {{
  font-family: -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background:{CREAM}; color:{GRAPHITE};
  -webkit-font-smoothing: antialiased;
}}
.card {{
  width:{CARD_W}px; height:{CARD_H}px;
  background:{CREAM};
  padding:48px 44px;
  display:flex; flex-direction:column;
  position:relative; overflow:hidden;
}}
.mono {{ font-family:"SF Mono","JetBrains Mono",Menlo,Consolas,monospace; }}
.phos {{ color:{PHOS}; }}
.ink {{ color:{INK}; }}
"""


def html_doc(body: str, extra_css: str = "") -> str:
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<style>{BASE_CSS}{extra_css}</style></head><body>{body}</body></html>"""


# ---------- 封面卡 ----------
def render_cover(date_str: str, n: int, hook: str) -> str:
    md = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m.%d")
    hook = esc(hook) or f"今日 {n} 条 AI 信号 · 3 分钟看懂"
    css = f"""
.cover {{ justify-content:space-between; }}
.cover .top {{ display:flex; align-items:center; gap:10px; }}
.cover .dot {{ width:13px; height:13px; border-radius:50%; background:{PHOS}; }}
.cover .kicker {{ font-size:17px; letter-spacing:2px; color:{GRAPHITE}; font-weight:600; }}
.cover .date {{ margin-left:auto; font-size:16px; color:{MIST}; }}
.cover .mid {{ flex:1; display:flex; flex-direction:column; justify-content:center; }}
.cover h1 {{ font-size:62px; line-height:1.12; font-weight:800; color:{INK}; letter-spacing:-1px; }}
.cover .count {{ display:inline-block; color:{PHOS}; }}
.cover .hook {{ margin-top:28px; font-size:24px; line-height:1.5; color:{GRAPHITE}; font-weight:500;
  position:relative; padding-left:18px; }}
.cover .hook::before {{ content:""; position:absolute; left:0; top:6px; bottom:6px; width:5px;
  background:{PHOS}; border-radius:3px; }}
.cover .foot {{ display:flex; align-items:center; gap:8px; font-size:17px; color:{BRICK}; }}
.cover .foot b {{ color:{INK}; font-weight:700; }}
"""
    body = f"""
<div class="card cover">
  <div class="top">
    <span class="dot"></span>
    <span class="kicker">AI 信号 · DAILY</span>
    <span class="date mono">{md}</span>
  </div>
  <div class="mid">
    <h1>今日<br><span class="count">{n}</span> 条<br>AI 信号</h1>
    <div class="hook">{hook}</div>
  </div>
  <div class="foot"><span class="dot" style="width:9px;height:9px;border-radius:50%;background:{PHOS};display:inline-block;"></span>&nbsp;<b>雷码工坊</b>&nbsp;· 每天三分钟，跟上 AI</div>
</div>"""
    return html_doc(body, css)


# ---------- 内容卡（信号卡）----------
def render_card(c: dict, idx: int, total: int, date_str: str) -> str:
    md = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m.%d")
    category = esc(c.get("category") or "AI")
    title = esc(c.get("title") or "")
    fact = esc(c.get("fact") or "")
    take = esc(c.get("take") or "")
    source = esc(c.get("source") or "")
    # 次级旁注用的浅色块（比米白背景略深，柔和区分「点评 ≠ 新闻」）
    TINT = "#EFEBDF"
    # 字号/间距全部 ×var(--k)，由 render_to_png 的自适应引擎测高后求解 k：
    # 内容短 → k>1 放大填满；内容长 → k<1 缩小不溢出。永远饱满、不留空档、不裁切。
    css = f"""
.sig {{ --k:1; }}
.sig .top {{ display:flex; align-items:center; gap:9px; margin-bottom:calc(24px * var(--k)); }}
.sig .dot {{ width:11px; height:11px; border-radius:50%; background:{PHOS}; flex:none; }}
.sig .cat {{ font-size:17px; font-weight:700; color:{INK}; }}
.sig .date {{ margin-left:auto; font-size:15px; color:{MIST}; }}
/* .fit 吃满 top 与 foot 之间的全部空间；.inner 居中，自适应引擎把它撑到刚好填满 */
.sig .fit {{ flex:1; min-height:0; display:flex; flex-direction:column; justify-content:flex-start; overflow:hidden; }}
.sig .inner {{ width:100%; }}
/* 事实是绝对主体——大号深色 */
.sig h2 {{ font-size:calc(34px * var(--k)); line-height:1.2; font-weight:800; color:{INK}; letter-spacing:-0.5px; }}
.sig .fact {{ margin-top:calc(22px * var(--k)); font-size:calc(22px * var(--k)); line-height:1.62; color:{INK}; font-weight:500; }}
/* 雷码视角：次级旁注，可选——缩小、变浅、加底色块，明显弱于新闻 */
.sig .take {{ margin-top:calc(24px * var(--k)); background:{TINT}; border-radius:14px;
  padding:calc(16px * var(--k)) calc(20px * var(--k)); position:relative; }}
.sig .take::before {{ content:""; position:absolute; left:0; top:15px; bottom:15px; width:5px;
  background:{PHOS}; border-radius:0 3px 3px 0; }}
.sig .take .label {{ font-size:calc(14px * var(--k)); font-weight:800; color:{PHOS}; letter-spacing:1.5px; margin-bottom:calc(5px * var(--k)); }}
.sig .take .body {{ font-size:calc(18px * var(--k)); line-height:1.55; color:{BRICK}; }}
.sig .foot {{ flex:none; padding-top:22px; display:flex; align-items:center; font-size:15px; color:{MIST}; }}
.sig .foot .src {{ color:{BRICK}; }}
.sig .foot .pg {{ margin-left:auto; }}
"""
    src_disp = f"来源 {source}" if source else ""
    # take 可选：没有就不渲染那块旁注，事实独占更多版面
    take_html = f"""
    <div class="take">
      <div class="label">雷码视角</div>
      <div class="body">{take}</div>
    </div>""" if take else ""
    body = f"""
<div class="card sig">
  <div class="top">
    <span class="dot"></span>
    <span class="cat">{category}</span>
    <span class="date mono">{md}</span>
  </div>
  <div class="fit"><div class="inner">
    <h2>{title}</h2>
    <div class="fact">{fact}</div>{take_html}
  </div></div>
  <div class="foot">
    <span class="src mono">{src_disp}</span>
  </div>
</div>"""
    return html_doc(body, css)


# ---------- 尾卡 CTA ----------
def render_cta() -> str:
    css = f"""
.cta {{ background:{INK}; align-items:flex-start; justify-content:center; }}
.cta .card-inner {{ width:100%; }}
.cta .badge {{ display:inline-flex; align-items:center; gap:8px; font-size:16px; color:{PHOS};
  letter-spacing:1px; font-weight:700; margin-bottom:30px; }}
.cta .badge .dot {{ width:10px; height:10px; border-radius:50%; background:{PHOS}; }}
.cta h2 {{ font-size:46px; line-height:1.25; font-weight:800; color:{CREAM}; letter-spacing:-0.5px; }}
.cta h2 .g {{ color:{PHOS}; }}
.cta .sub {{ margin-top:24px; font-size:21px; line-height:1.6; color:#C9CDD6; }}
.cta .line {{ width:60px; height:5px; background:{PHOS}; border-radius:3px; margin:36px 0 28px; }}
.cta .wx {{ font-size:20px; line-height:1.7; color:{CREAM}; }}
.cta .wx b {{ color:{PHOS}; }}
.cta .foot {{ position:absolute; left:44px; bottom:48px; font-size:16px; color:{MIST}; }}
"""
    body = f"""
<div class="card cta">
 <div class="card-inner">
  <div class="badge"><span class="dot"></span>雷码工坊 · LEIMA WORKS</div>
  <h2>每天 <span class="g">3 分钟</span>，<br>跟上 AI 真正发生的事</h2>
  <div class="sub">不聊概念，只聊真实发生的事。<br>产品人视角，看 AI 怎么重塑工作。</div>
  <div class="line"></div>
  <div class="wx">点赞 · 收藏 · 关注 <b>雷码工坊</b><br>每天 3 分钟，不错过 AI 真正发生的事</div>
 </div>
 <div class="foot mono">关注我 · 每天看懂 AI →</div>
</div>"""
    return html_doc(body, css)


# ---------- 截图 ----------
# 自适应填充引擎：测 .inner 自然高度 vs .fit 可用高度，迭代求解缩放系数 --k，
# 让内容刚好填满 top 与 foot 之间的空间（目标 FILL）。内容短则放大、长则缩小。
# k 夹在 [K_MIN, K_MAX]：放大有上限（短内容不会大到失真），缩小有下限（长内容到底也保可读，
# 真撑不下由 card overflow:hidden 兜底，但 220 字内实测都在范围内）。
_FIT_JS = """() => {
  const fit = document.querySelector('.fit');
  const inner = document.querySelector('.fit .inner');
  if (!fit || !inner) return 1;
  const FILL = 0.98, K_MIN = 0.40, K_MAX = 1.5, SAFE = 0.995;
  const sig = document.querySelector('.sig');
  let k = 1, bestFit = 0;          // bestFit = 见过的「不溢出」里最大的 k
  sig.style.setProperty('--k', k.toString());
  for (let i = 0; i < 20; i++) {
    const avail = fit.clientHeight;
    const need = inner.scrollHeight;   // 反映当前 --k 的真实渲染高度
    if (!need) break;
    // 当前档不溢出就记为候选——这一步是关键：
    // 行折叠是离散的，need∝k² 的平滑假设在「某行刚好折行」的临界点会断裂，
    // sqrt 步长会在「有空隙」和「溢出」两档间来回震荡、永不满足收敛判据，
    // 循环跑满后可能正好停在溢出档导致裁字。所以只认记录到的最大安全档。
    if (need <= avail * SAFE && k > bestFit) bestFit = k;
    let nk = k * Math.sqrt(avail * FILL / need);
    nk = Math.max(K_MIN, Math.min(K_MAX, nk));
    if (Math.abs(nk - k) < 0.003) { k = nk; break; }   // 平滑收敛（短内容常走这条）
    k = nk;
    sig.style.setProperty('--k', k.toString());
  }
  // 终值：优先用记录到的最大安全档（绝不停在震荡的溢出档）；一档都不安全才退到 K_MIN（极长内容，由 overflow:hidden 兜底）
  const finalK = bestFit > 0 ? bestFit : K_MIN;
  sig.style.setProperty('--k', finalK.toString());
  return finalK;
}"""


def render_to_png(html_str: str, out_path: Path, fit: bool = False) -> None:
    from playwright.sync_api import sync_playwright
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": CARD_W, "height": CARD_H},
            device_scale_factor=SCALE,  # 540×720 @6x = 3240×4320 (3:4)
        )
        page = ctx.new_page()
        page.set_content(html_str, wait_until="networkidle")
        page.wait_for_timeout(200)
        if fit:
            page.evaluate(_FIT_JS)       # 内容卡：自适应缩放填满
            page.wait_for_timeout(60)
        page.screenshot(path=str(out_path), clip={"x": 0, "y": 0, "width": CARD_W, "height": CARD_H}, type="png")
        browser.close()


SAMPLE = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "hook": "模型、编程、商业三条线，今天都有大事",
    "cards": [
        {
            "category": "模型发布",
            "title": "Claude Opus 4.8 上线百万上下文",
            "fact": "Anthropic 发布 Opus 4.8，原生支持 100 万 token 上下文，长文档与整库代码可一次性读入，编码与 agent 任务表现刷新此前纪录。",
            "take": "对做长文档分析和大型代码库的人，这是质变——以前要切片喂、做 RAG，现在直接整本塞进去。上下文窗口正在从「技巧活」变成「默认能力」。",
            "source": "@AnthropicAI",
        },
        {
            "category": "AI 编程",
            "title": "Cursor 宣布支持后台 agent 并行跑任务",
            "fact": "Cursor 上线后台 agent，可同时派多个任务并行执行、互不阻塞，完成后回写结果，开发者不必盯着单线程等待。",
            "take": "编程工具的竞争点正从「补全多准」转向「能不能托管整条任务」。谁先把「派活—并行—验收」这套跑顺，谁就拿下下一代开发心智。",
            "source": "@cursor_ai",
        },
        {
            "category": "AI 商业",
            "title": "OpenAI 据传新一轮融资估值再翻倍",
            "fact": "据多家媒体报道，OpenAI 正洽谈新一轮融资，估值较上轮接近翻倍，资金主要投向算力与企业级产品扩张。",
            "take": "估值数字本身不重要，重要的是钱流向哪——算力和企业级，说明大厂赌的是「AI 进生产系统」而非消费玩具。B 端才是这轮真正的战场。",
            "source": "@OpenAI",
        },
    ],
    "caption": "今天的 AI 三条线都有动作：模型、编程、商业。\n点开看每条信号 + 雷码工坊视角。",
    "tags": ["#AI", "#人工智能", "#ClaudeCode", "#AI编程", "#智能体", "#OpenAI"],
}


def build_deck(data: dict, out_dir: Path) -> list[Path]:
    date_str = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    cards = data.get("cards") or []
    n = len(cards)
    out_dir.mkdir(parents=True, exist_ok=True)
    # 清掉上次的旧图，避免卡片数变化时残留（如 3 条 → 4 条时旧的尾卡）
    for old in out_dir.glob("*.png"):
        old.unlink()
    paths = []

    # 内容卡（第 1 张即小红书封面图，无独立封面页）
    # 注：尾卡 CTA 已移除（含「关注我」字样，小红书跨平台易被拦截/降权）；
    #     render_cta() 函数保留备查，但不再进图组。
    for i, c in enumerate(cards, 1):
        p = out_dir / f"{i:02d}.png"
        render_to_png(render_card(c, i, n, date_str), p, fit=True)
        paths.append(p)
        print(f"  ✓ {p.name}  {c.get('title','')[:24]}", flush=True)

    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="选好题的 JSON 路径")
    ap.add_argument("--date", help="YYYY-MM-DD（缺省今天）")
    ap.add_argument("--sample", action="store_true", help="用内置样例数据跑通最小闭环")
    args = ap.parse_args()

    load_env()
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    if args.sample:
        data = dict(SAMPLE)
        data["date"] = date_str
    else:
        inp = Path(args.input) if args.input else (XHS_DIR / f"{date_str}.json")
        if not inp.exists():
            sys.exit(f"输入 JSON 不存在：{inp}（先跑选题分析，或用 --sample 测试）")
        data = json.loads(inp.read_text())
        data.setdefault("date", date_str)

    out_dir = XHS_DIR / data["date"]
    print(f"渲染图组 → {out_dir}", flush=True)
    paths = build_deck(data, out_dir)
    print(f"\n完成：{len(paths)} 张图（{len(data.get('cards') or [])} 条新闻，无尾卡）", flush=True)

    # 文案落盘（方便人工复制到小红书）——标题 / 描述 / 标签 分开
    title = (data.get("xhs_title") or data.get("hook") or "").strip()
    caption = (data.get("caption") or "").strip()
    tags = " ".join(data.get("tags") or [])
    if title or caption or tags:
        cap_path = out_dir / "caption.txt"
        parts = []
        if title:
            parts.append(f"【标题】\n{title}")
        if caption:
            parts.append(f"【描述】\n{caption}")
        if tags:
            parts.append(f"【标签】\n{tags}")
        cap_path.write_text("\n\n".join(parts) + "\n")
        print(f"文案 → {cap_path}", flush=True)


if __name__ == "__main__":
    main()
