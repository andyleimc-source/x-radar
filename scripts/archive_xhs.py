#!/usr/bin/env python3
"""
X Radar · 小红书每期发布归档

把当天渲染好的图片 + 选题 JSON 归档到 posts/<date>/：
- 拷贝最终图片（01.png … NN-cta.png）到 posts/<date>/
- 生成 post.md：小红书标题 / 正文介绍 / 标签 / 图片顺序 / 来源自查 / 发布状态
  （可直接复制 post.md 里的标题+正文+标签发小红书）

posts/ 是「发布归档」（每期一个文件夹），和工作区 data/xhs/（临时、会被覆盖）分开。
约定：post.md 入 git（编辑记录），图片不入 git（见 .gitignore），本地留着能看能传。

用法：
    python3 scripts/archive_xhs.py [--date YYYY-MM-DD]
"""
import argparse
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XHS_DIR = ROOT / "data" / "xhs"
POSTS_DIR = ROOT / "posts"
# 桌面成品库：每次生成都按日期建子文件夹，图 + 文案一站式取用
DESKTOP_DIR = Path.home() / "Desktop" / "小红书AI日报"


def strip_follow_cta(text: str) -> str:
    """兜底删掉文案里任何含「关注」的句子（如「关注雷码工坊…」）——
    小红书引导关注会降权；prompt 已禁，这里再防一道旧 JSON / 模型漏网。"""
    if not text:
        return text
    sentences = re.split(r"(?<=[。！!？?\n])", text)
    kept = [s for s in sentences if "关注" not in s]
    return "".join(kept).strip().strip("，,、；; ").strip() or text


def build(date_str: str) -> Path:
    json_path = XHS_DIR / f"{date_str}.json"
    img_dir = XHS_DIR / date_str
    if not json_path.exists():
        raise SystemExit(f"选题 JSON 不存在：{json_path}（先跑 analyze_xhs.py）")
    pngs = sorted(img_dir.glob("*.png"))
    if not pngs:
        raise SystemExit(f"没有图片：{img_dir}（先跑 render_xhs.py）")

    data = json.loads(json_path.read_text())
    cards = data.get("cards") or []
    hook = (data.get("hook") or "").strip()
    xhs_title = (data.get("xhs_title") or "").strip()
    caption = strip_follow_cta((data.get("caption") or "").strip())
    tags = data.get("tags") or []

    out_dir = POSTS_DIR / date_str
    out_dir.mkdir(parents=True, exist_ok=True)

    # 拷图（清掉旧的避免条数变化残留）
    for old in out_dir.glob("*.png"):
        old.unlink()
    for p in pngs:
        shutil.copy2(p, out_dir / p.name)

    # 图片顺序清单（已无尾卡，全部是内容图）
    img_lines = []
    content = [p for p in pngs if "cta" not in p.stem]
    for i, p in enumerate(content):
        c = cards[i] if i < len(cards) else {}
        cat = c.get("category", "")
        title = c.get("title", "")
        img_lines.append(f"{i+1}. `{p.name}` — [{cat}] {title}")

    # 来源自查（仅供本人核对，勿放进小红书正文——带链接会被封）
    src_lines = [f"- [{c.get('category','')}] {c.get('title','')} — {c.get('source','')}" for c in cards]

    tag_line = " ".join(tags)
    # 小红书标题：优先用 ≤20 字的 xhs_title，回退 hook，再回退首条标题
    title_for_xhs = xhs_title or hook or (cards[0].get("title", "") if cards else "今日 AI 信号")

    # 一键复制块：标题 + 描述 + 标签，三段合一，复制一次即可贴小红书
    copy_block = f"{title_for_xhs}\n\n{caption}\n\n{tag_line}".strip()

    md = f"""# 雷码工坊 · 今日 AI 信号 · {date_str}

> {len(content)} 条新闻 · 共 {len(pngs)} 图 · 3:4 / 3240×4320

## 📋 一键复制（标题 + 描述 + 标签，复制这一段即可发布）
```
{copy_block}
```

## 🖼 图片顺序（按此顺序上传，第 1 张即封面）
{chr(10).join(img_lines)}

## 🔗 来源自查（仅供本人核对，**勿放进正文**——带链接会被小红书封）
{chr(10).join(src_lines)}

## ✅ 发布状态
- [ ] 已发布到小红书
- 发布时间：
- 笔记链接：
- 数据（赞/藏/评）：
"""
    (out_dir / "post.md").write_text(md)

    # 同步到桌面成品库：~/Desktop/小红书AI日报/<date>/（图 + 文案.txt 一站取用）
    desk = DESKTOP_DIR / date_str
    desk.mkdir(parents=True, exist_ok=True)
    for old in desk.glob("*.png"):
        old.unlink()
    for p in pngs:
        shutil.copy2(p, desk / p.name)
    (desk / "文案.txt").write_text(copy_block + "\n")
    print(f"🖥  桌面成品 → {desk}")

    return out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = ap.parse_args()
    out = build(args.date)
    n_png = len(list(out.glob("*.png")))
    print(f"✅ 已归档 → {out}  （{n_png} 图 + post.md）")


if __name__ == "__main__":
    main()
