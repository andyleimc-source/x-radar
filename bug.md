# Bugs & Known Issues

格式：状态 | 现象 | 根因 | 修复 | 日期

---

## OPEN
_（暂无）_

## FIXED

### 2026-07-01 · 卡片自适应引擎在折行临界点震荡 → 长文卡底部裁字
- **现象**：长 fact 卡片（如 07-01 Netflix 那条，标题 3 行 + fact 161 字）底部正文被页脚裁掉半行，排版「断了」
- **根因**：`render_xhs.py` 的 `_FIT_JS` 自适应引擎用 `nk = k·√(avail·FILL/need)` 迭代求缩放系数，假设 `need ∝ k²`。但行折叠是**离散**的——某行刚好折/不折的临界点会让 `need` 阶跃（实测在 k≈1.24↔1.28 间 need 在 483↔551 跳 ~2 行），打破平滑假设。引擎在「有空隙→放大」和「溢出→缩小」两档间**反复横跳、永不满足 `|nk-k|<0.003` 收敛判据**，循环跑满 18 次后**正好停在溢出那一档**（k=1.284，溢出 25px）→ `.fit` 的 `overflow:hidden` 从半行裁掉
- **修复**：循环中记录「见过的不溢出档里最大的 k」（`bestFit`，判据 `need ≤ avail·0.995`），结束时一律用 `bestFit` 而非最后一次迭代的 k——绝不停在震荡的溢出档；一档都不安全才退 `K_MIN`（=0.40，由 overflow 兜底）。同 commit 顺手去掉卡片右下角 `{idx}/{total}` 页码（Andy 不要数字标识）
- **验证**：重渲染 07-01 全组，09(Netflix) 整条 fact 完整收尾不裁、01 等短卡仍饱满

### 2026-06-29 · bash `set -u` 下 `$var` 紧跟中文全角标点被当未定义变量
- **现象**：`deliver-xhs.sh`/`build-xhs.sh` 报 `DATE\x1f: unbound variable`、`JSON\x1f: unbound variable` 之类，脚本中途崩。隐蔽点：正常路径不一定触发（如 `$JSON（…）` 在回退分支才走到），测试时漏过
- **根因**：`echo "...slug=xhs-$DATE）..."` 这种 `$DATE` 后紧跟全角括号「）」「，」等多字节字符，bash 在 `set -u`（nounset）下把多字节首字节误并进变量名 → 该名未定义 → 报错。**所有 `set -euo pipefail` 的脚本只要 `$var` 后面直接跟中文标点都会中招**
- **修复**：一律用 `${var}` 花括号界定（`${DATE}）`）。已扫全 `scripts/*.sh` 根除：`grep -rnP '\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F]' scripts/*.sh` 应为空
- **教训**：中文脚本里 `$var` 后跟任何非 ASCII 字符，一律 `${var}`

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
