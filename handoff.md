# Handoff

给下一轮 Claude 会话的交接备忘。每次会话结束前更新。

---

## 🔭 停泊任务（指针）

- **📌 图组任务卡剩余两件**（2026-07-01 建）→ 见 `plan.md` › M4 待办末「任务卡 · 图组去重 + 转发文案改造 + 预览页瘦身」。**目标 1 跨日去重已做完（2026-07-02，全量历史版）**；标签≤5 也已做。剩：② 转发文案合成一整段（标题≤15、正经不浮夸、不露「标题/描述/标签」字段名）；③ 预览页去图、文案置顶。
- **🔧 Reddit 改 OAuth 稳定方案**（2026-07-01 研究完，待 Andy 给 client_id/secret）：Reddit 2026-06-11 起对 RSS 也限流（429）。方案=注册 script 类型 app 走 `client_credentials` OAuth → `oauth.reddit.com` JSON，100 QPM，纯 stdlib 改 `scripts/external.py:fetch_reddit`。Andy 去 reddit.com/prefs/apps 拿 id/secret 后写进 `.env`（`REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`）即可动手。

---

## 本轮增量（2026-07-02）

- 图组已交付今日版（预览 `xhs-2026-07-02`），分辨率永久翻倍 **3240×4320**（`render_xhs.py` SCALE=6），标签硬上限 5
- **跨日去重已上线**：`posts/history.jsonl`（入 git）= 每天已发条目落盘（archive 自动 upsert）；`analyze_xhs.py` 按历史 URL 程序剔除 + 近 400 条标题喂模型 + prompt 规则 4.5。以后每天自动生效，无需手动
- 注意：`data/xhs/<date>.json` 的卡片现在带 `url` 字段（src_id 回填），老 JSON 没有属正常

## 当前状态（2026-05-06）

- 主管线稳定（远程 crontab 06:00 → `send-digest.sh morning` → digest + 邮件）
- **关注列表 53 账号**（含 Claude Code/Codex/Cursor 同行、AI 重磅、SaaS 老兵、中文圈）
- prompt 已升级：⭐ 精选 + 📎 其他 + ✍️ **写作选题建议 5–7 条**（热点/争议/爆款 + ≥1 工具向，结合 PH/GH trending）
- 邮件末尾已带 **DeepSeek v4-flash 账单**（命中/未命中/输出 token + ¥）；价格常量在 `scripts/digest.py` 顶部，决策落 `decision.md`
- 邮件发到 `leimingcan@icloud.com`（email-mcp `work` 账号 andy.lei@mingdao.com）
- 海报长图脚本 `scripts/render_poster.py` 仍是本地雏形，未接管线
- ⚠️ **服务器 `/home/ubuntu/xradar` 有未提交改动**（`config/settings.yaml` / `scripts/digest.py` / `scripts/fetch_tweets.sh` 早就 M 状态）。本次同步用 scp 直接覆盖了 `accounts.yaml` / `analysis.md` / `digest.py`，没动 git。下次部署前先看一眼这几个 M 文件到底是什么差异，决定 commit 还是丢

## 下一轮该做什么（按优先级）

1. **先看明早 06:00 第一次跑的真实效果**：53 账号全量摘要 + 5–7 条写作选题 + 账单。选题不够爆 / 工具向那条不强 → 调 `prompts/analysis.md` 末尾「✍️ 写作选题建议」规则
2. 看 `plan.md`：**M1 信息源扩展（HN+Reddit）** 优先；HN 无凭证可立即写
3. 处理上面 ⚠️ 的服务器未提交改动

## 环境

- 部署：腾讯云硅谷 `ubuntu@170.106.146.222`，代码 `/home/ubuntu/xradar`，凭证见 `.local/servers.md`
- 调度：服务器 crontab（Asia/Shanghai），`0 6 * * * /bin/bash /home/ubuntu/xradar/scripts/send-digest.sh morning`
- 本机不跑任何调度（本机 launchd plist 出现就删）

## 注意事项

- **API 费/调用钱要先确认再执行**（全局 CLAUDE.md 红线）
- **不接回 launchd / Hermes / 本机 cron**（决策已定）
- **微信推送已砍，不要复活**
- 海报 / XHS 走本机，**不要往远端塞 Chromium**
- 公网服务必须有鉴权（全局红线，xradar 当前无公网端口暴露）
