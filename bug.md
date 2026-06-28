# Bugs & Known Issues

格式：状态 | 现象 | 根因 | 修复 | 日期

---

## OPEN
_（暂无）_

## FIXED

### 2026-06-28 · vibeshare 部署预览页只剩占位页「Nothing to see here」
- **现象**：`vibeshare preview.html --force --json` 返回 `ok:true`，但线上访问只有 511 字节的占位页，内容没上去
- **根因**：预览 HTML 把 8 张 1080×1440 PNG base64 内嵌，单文件 3.2MB，**超过 vibeshare/Firebase 单文件体积上限**（实测 1MB 能传、3.2MB 不能，限在两者之间），CLI 静默只部署了占位页
- **修复**：`preview_xhs.py` 内嵌前用 PIL 把图缩到宽 600px + JPEG q78（`img_b64`），单文件砍到 ~1MB，部署后线上内容正常。注意浏览器可能缓存了旧占位页，需硬刷新
- **教训**：vibeshare 部署单文件务必 < 1MB；图片预览页一律先缩 JPEG，别内嵌全分辨率 PNG

### 2026-06-28 · HN Algolia 抓取全部 400（影响主 digest + xhs 选题）
- **现象**：`fetch_hn` 一直 `HTTP Error 400`，HN 板块在邮件 digest 和小红书选题里都拿不到任何条目（静默降级，之前没发现）
- **根因**：Algolia 收紧了 HN 索引设置，`points` 不再是可过滤数值属性——`numericFilters=...,points>=50` 直接 400（响应体：`invalid numeric attribute(points), attribute not specified in numericAttributesForFiltering`）
- **修复**：改用 `search_by_date` 端点，服务端只用 `created_at_i>ts` 过时间窗（取窗口内最新 100 条），`points>=min_points` 改本机过滤（commit 见下）。`created_at_i` 仍是合法可过滤属性
- **验证**：本机 `fetch_hn(limit=8)` 正常返回带分数的 AI 故事

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
