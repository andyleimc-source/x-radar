# Handoff

给下一轮 Claude 会话的交接备忘。每次会话结束前更新。

---

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
