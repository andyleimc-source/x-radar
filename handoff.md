# Handoff

给下一轮 Claude 会话的交接备忘。每次会话结束前更新。

---

## 当前状态（2026-04-30）

- 主管线（远程 crontab 06:00 → `send-digest.sh morning` → digest + 邮件）稳定运行
- 邮件发到 `leimingcan@icloud.com`，发件账号 `andy.lei@mingdao.com`（email-mcp `work`）
- LLM 走 DeepSeek V4 Flash（`.env` 里 `DEEPSEEK_API_KEY`）
- 海报长图脚本 `scripts/render_poster.py` 有本地雏形，未接管线
- 项目协作骨架文件刚拆分完毕（plan / progress / decision / bug / handoff）

## 下一轮该做什么

1. 先读 `CLAUDE.md`（架构、部署、排查命令）
2. 看 `plan.md` 确定开工哪条线：**M1 信息源扩展 / M2 海报接管线 / M3 小红书**
3. 优先建议 M1（HN 无凭证，可立即写；Reddit 需先注册 OAuth app）

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
