# Bugs & Known Issues

格式：状态 | 现象 | 根因 | 修复 | 日期

---

## OPEN
_（暂无）_

## FIXED

### 2026-04 · digest.py 失败时仍发旧 digest
- **现象**：digest 生成失败但邮件照发，发出来的是上一次的内容
- **修复**：`send-digest.sh` 在 `digest.py` 失败时立即退出，不再继续发邮件（commit 821997c）

### 早期 · email Resend 请求被拒
- **现象**：Resend API 调用返回错误
- **根因**：缺 `User-Agent` header
- **修复**：补 `User-Agent`（commit e7caa6b）

### 早期 · digest 解析 twitterapi.io 响应失败
- **现象**：拿不到 tweets
- **根因**：响应是嵌套 `data.data.tweets` 信封
- **修复**：unwrap 嵌套结构（commit 0bf0d12）
