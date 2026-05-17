# 作者库 + 每日「今日作者介绍」模块 · Design

日期：2026-05-17
状态：Draft（待 Andy review）

## 目的

让 Andy 通过了解作者来理解"这个人为什么写这篇文章"，并从作者经历中获取启发。每日 digest 倒数第二个模块（在 ✍️ 写作建议之前）展示 3 位当天上榜作者的画像。

## 范围

- **入库范围**：X 关注列表里的固定账号 + Podcast 节目主播。
- **不入库**：HN 作者/评论员（多为匿名 ID，ROI 低）、Podcast 嘉宾（一次性）。

## 数据模型

文件：`config/authors.yaml`，单文件平铺数组。

```yaml
- handle: lennysan          # 唯一 ID（X handle 或 podcast slug）
  source: x                 # x | podcast
  name: Lenny Rachitsky
  bio: 前 Airbnb 产品负责人，2020 起全职做 Lenny's Newsletter…
  career: |
    - 2010-2020 Airbnb Product Lead
    - 2020-now Lenny's Newsletter 创始人
  expertise: [产品增长, PM 职业, SaaS metrics]
  positioning: 全球付费订阅最多的 PM newsletter（70 万+）
  ai_comment: 大厂 PM 转独立创作者的样板，可参考其访谈飞轮玩法
  sources:                  # Jina 搜索引用 URL，事后可核查
    - https://...
    - https://...
  generated_at: 2026-05-17
  locked: false             # true 时 build_author.py 跳过覆盖
```

字段全是字符串/列表，无 schema 验证。Andy 手改后可设 `locked: true` 防止下次覆盖。

## 数据来源

- **搜索**：`https://s.jina.ai/<query>` —— 免费、不带 key、20 次/分钟。
- **综述**：DeepSeek V4 Flash（已在用），将搜索片段喂给 prompt 生成结构化画像。
- **不联网纯 LLM 生成 = 编造**，禁止。Prompt 显式要求"搜索结果里没有的事实不要写，留空"。

## 流程

### 入库（新作者）

由 `digest.py` 在抓完推文后触发，对所有"不在 authors.yaml 里"的 handle 调用 `scripts/build_author.py <handle> <source>`。

单作者流程（约 10 秒）：

1. 拼 query：`<name or handle> 履历 创业 现状 background`
2. `GET https://s.jina.ai/<query>` 拿前 5 条结果（标题 + 片段 + url）
3. 把片段拼进 `prompts/author.md` → DeepSeek 输出 YAML 片段
4. append 到 `config/authors.yaml`

**失败处理**：Jina 超时/无结果 → 写一条 `bio: "[待补全]"` 占位，`locked: false`，下次跑重试。不阻塞主流程。

**手动重建**：`python3 scripts/build_author.py <handle> --force`（无视 locked）。

**初始批量建库**：一次性脚本 `scripts/build_authors_bulk.sh` 扫 `config/accounts.yaml` 所有 X 账号 + podcast 主播。约 40 人 × 10 秒 ≈ 7 分钟，Jina 速率限制下 sleep 3 秒/次。

### 每日选 3 人 + 注入

`digest.py` 生成 digest 主体之后再做一次 LLM 调用：

1. 拿当天 digest 里出现的所有作者 + 对应文章标题/摘要
2. 喂给 DeepSeek（用 `prompts/author_select.md`），返回 3 个 handle
3. 从 `authors.yaml` 读对应字段，渲染成 markdown 块
4. **插入到「✍️ 写作建议」之前**（倒数第二模块）

为什么 LLM 选而非规则：Andy 的标准是"价值/启发度"，本是 LLM 强项；规则（点赞/转发）会偏向流量大 V，错过冷门高质。

**边界**：当天作者 ≤ 3 → 全列；= 0 → 整块不出现。

### 输出格式（渲染到 digest）

```markdown
## 👤 今日作者介绍

### Lenny Rachitsky (@lennysan)
前 Airbnb 产品负责人，2020 起全职做 Lenny's Newsletter…

**履历**：Airbnb PM Lead (2010-2020) → Lenny's Newsletter 创始人
**擅长**：产品增长 / PM 职业 / SaaS metrics
**定位**：全球付费订阅最多的 PM newsletter（70 万+）
**🤖 AI 点评**：大厂 PM 转独立创作者的样板，可参考其访谈飞轮玩法

---

### Andrej Karpathy (@karpathy)
...
```

## 改动清单

**新增**：
- `config/authors.yaml` — 作者库（初始空）
- `scripts/build_author.py` — 单作者建档
- `scripts/build_authors_bulk.sh` — 一次性批量建初始库
- `prompts/author.md` — 作者画像生成 prompt
- `prompts/author_select.md` — 每日选 3 人 prompt

**修改**：
- `scripts/digest.py` — 两个钩子：
  1. 抓完推文后对新 handle 调 `build_author.py`
  2. 生成 digest 后调"选 3 + 渲染作者块"，拼到「✍️ 写作建议」前
- `prompts/analysis.md` — 不改（作者块在 digest 外拼接）

**配置**：
- `.env` 无新增（Jina 免费档不需 key）
- 若引入 podcast 主播，`config/accounts.yaml` 的 podcasts 段需带 `host_handle` 字段

## Prompt 设计要点

### `prompts/author.md`

```
基于以下搜索结果，为 <name> (@<handle>) 生成作者画像。
严格要求：
- 不要编造。搜索结果里没有的事实不要写。
- 信息不足时字段留空字符串，不要瞎填。
- ai_comment 一句话，从 Andy 视角（明道云 CMO + 独立创作者）写
  "为什么值得读他 / 能学什么"。

输出 YAML（字段：bio, career, expertise, positioning, ai_comment）。

搜索结果：
{snippets}
```

### `prompts/author_select.md`

```
从以下今日上榜作者中，按"文章价值/热度/对 Andy 的启发度"综合选 3 位。
Andy 是明道云 CMO + 独立创作者，关注 AI、PM、增长、独立创业。

作者列表：
- @lennysan：文章《...》摘要：...
- @karpathy：文章《...》摘要：...

输出：3 个 handle，逗号分隔，无解释。
```

## 风险 / 取舍

1. **Jina 免费档 20 次/分钟**：批量建库需 sleep 3 秒/次；日常增量无问题。
2. **LLM 选择不稳定**：每日选的 3 人有抖动；可接受，目标是"多样曝光"而非"客观排名"。
3. **首次跑会慢**：约 7 分钟建初始库；之后只为新作者跑。
4. **Jina 搜索质量**：中文搜冷门作者可能片段稀薄 → 占位 `[待补全]`，Andy 可手填后 `locked: true`。
5. **作者识别口径**：HN/Podcast 嘉宾不入库已确认。Podcast 主播 handle 需在 `accounts.yaml` 显式声明。

## YAGNI 已砍

- ❌ SQLite / DB（几十条数据不值得）
- ❌ Perplexity API（$50 起充值，对此用量浪费）
- ❌ 抓 X bio 作画像基础（用户砍掉了"画像数据"层级，只保留 LLM + 联网搜索）
- ❌ schema 校验（YAML 字段全是字符串/列表，错了就重跑）
- ❌ 作者画像 web UI（md 直接编辑足够）

## 验收

- `config/authors.yaml` 存在且至少一条记录
- 任意一天 digest 末尾出现「👤 今日作者介绍」模块（除非当日 0 作者命中库）
- 模块位置在「✍️ 写作建议」之前
- 每个作者卡片含：bio、履历、擅长、定位、AI 点评
- `build_author.py` 跑同一 handle 两次：第二次因为已存在直接跳过（除非 `--force`）
