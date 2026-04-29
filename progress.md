# Progress

按时间倒序记录。每条包含：日期、做了什么、结果、下一步。

---

## 2026-04-30
- 项目结构化：拆分 `CLAUDE.md` 中「待开发」「为什么这么拆」等内容到 `plan.md` / `decision.md` / `progress.md` / `handoff.md` / `bug.md`
- 下一步：开工 M1（HN + Reddit 信息源接入）

## 2026-04-29
- 记录 HN + Reddit 接入计划到 `CLAUDE.md`（commit 0087677）

## 2026-04-28（前后）
- 升级到 DeepSeek V4 Flash（commit 7fa6cdd）
- fetch 改用 advanced_search + since_time 服务端过滤，省 ~80% API 费（commit 84dadae）

## 2026-04-24
- 调度降频到 1 次/天（仅 06:00）以节省 twitterapi.io 用量（commit 45711cb）

## 2026-04-23
- 海报长图生成器雏形：`scripts/render_poster.py`，Playwright 渲染 430 CSS px @3x 竖版 PNG（commit 3054936）
- twitterapi.io 用量追踪 + 邮件页脚展示（commit 76f8e91）
- 未接入 cron / send-digest.sh / 远端服务器

## 更早
- 圈外热点换成 Product Hunt + GitHub Trending（commit a89dad9）
- 两层 digest：⭐ 精选 + 📎 其他（按领域分组）（commit ce90c9b）
- email rich inline-CSS 模板（commit 5bf7a13）
- 重写 digest 管线为纯 Python + DeepSeek V3（commit cd9e5fd）
- 砍 Hermes+WeChat，切到 launchd（commit 3a312b7，后又迁到远程 crontab）
