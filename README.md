# eval-failure-clusterer

`eval-failure-clusterer` 是一个离线 Python CLI，用来读取 AI eval / LLM 应用评测结果，把失败按错误类型、标签、文本指纹、字段缺失、延迟和成本异常进行聚类，并输出修复优先级、样例包、报告和 CI gate。它面向希望在不依赖 embedding 或 LLM API 的情况下，快速理解失败分布、定位回归、安排修复顺序的团队。

## 为什么做这个工具

LLM 应用的 eval 结果往往分散在 JSONL、CSV、CI artifact、日志导出和断言输出中。团队常见痛点包括：

- 失败很多，但其实是少数几类根因在重复出现。
- 同一类失败跨模型、标签和测试集出现，人工翻看很慢。
- 延迟或成本回归经常和准确性失败一起出现，难以统一分析。
- baseline 对比只看到总通过率，看不到“哪一类失败在变严重”。

这个项目把这些问题统一成一个离线分析流程。

## 核心能力

- 读取 JSONL 和 CSV。
- 自动推断 pass/fail。
- 对失败原因做规则归一化。
- 使用 shingle + simhash 风格指纹进行近似文本聚类。
- 按标签、模型、用例维度生成汇总。
- 检测延迟和成本异常。
- 与 baseline 对比回归和改善。
- 计算修复优先级。
- 导出 brief / Markdown / JSON / CSV / JUnit / SARIF 报告。
- 生成样例包，便于修复和复现。
- 支持 CI gate，返回 warning 或 error。
- 支持 reviewed baseline，把已审阅历史失败登记为 JSON，让 CI 只拦截新增或未审阅失败 cluster；延迟、成本和显式 baseline 对比回归仍会照常报告。

## 安装

```bash
python -m pip install .
```

安装后可用命令：

```bash
eval-failure-clusterer --help
```

## 输入格式

工具会自动从常见字段中推断语义，也支持通过配置文件显式映射。

常见输入字段：

- `id` / `case_id` / `test_name`
- `status` / `passed` / `success` / `score`
- `error` / `failure_reason` / `assertion_message`
- `output` / `model_output` / `response`
- `model`
- `tags`
- `latency_ms`
- `cost_usd`
- `expected`
- `actual`

### JSONL 示例

```json
{"id":"qa-001","status":"fail","model":"gpt-lite","tags":["retrieval","zh"],"error":"Expected citation field missing","output":"Answer without citations","latency_ms":1400,"cost_usd":0.023}
{"id":"qa-002","passed":true,"model":"gpt-lite","tags":["retrieval","en"],"output":"Answer with citation","latency_ms":830,"cost_usd":0.018}
```

### CSV 示例

```csv
case_id,status,model,tags,error,output,latency_ms,cost_usd
qa-003,fail,gpt-pro,"reasoning;math",Assertion failed: missing final answer,"Long chain of thought",2100,0.041
```

## 快速开始

使用示例数据跑完整流程：

```bash
eval-failure-clusterer cluster examples/eval_results.jsonl --output outputs/demo
eval-failure-clusterer cluster examples/eval_results.jsonl --format brief,sarif --output outputs/triage
eval-failure-clusterer sample examples/eval_results.jsonl --output outputs/demo/samples --max-per-cluster 2
eval-failure-clusterer compare examples/baseline_eval.jsonl examples/eval_results.jsonl --output outputs/demo/compare
eval-failure-clusterer baseline examples/eval_results.jsonl --output eval-failure-baseline.json
eval-failure-clusterer check examples/eval_results.jsonl --reviewed-baseline eval-failure-baseline.json --output outputs/demo/check --check error
eval-failure-clusterer check examples/eval_results.jsonl --output outputs/demo/check --check error
```

## CLI

### `cluster`

```bash
eval-failure-clusterer cluster INPUT [--config config.json] [--output DIR] [--format brief,markdown,json,csv,junit,sarif]
```

输出：

- `brief.md`
- `summary.md`
- `clusters.json`
- `clusters.csv`
- `junit.xml`
- `clusters.sarif`

`brief.md` 适合直接贴到 PR、Slack 或交给 Codex/Claude Code，内容包含决策、失败率、Top cluster、样例 case id 和下一步建议。`clusters.sarif` 可上传到 GitHub Code Scanning 或其他支持 SARIF 2.1.0 的质量平台。

### `sample`

```bash
eval-failure-clusterer sample INPUT [--config config.json] [--output DIR] [--max-per-cluster 3] [--seed 7]
```

从每个 cluster 中抽样失败用例，生成 `samples.json` 和 `samples.md`。

### `compare`

```bash
eval-failure-clusterer compare BASELINE CANDIDATE [--config config.json] [--output DIR]
```

输出 baseline 与 candidate 的整体指标变化、cluster 级别回归、异常变化和新增失败类型。

### `baseline`

```bash
eval-failure-clusterer baseline INPUT [--config config.json] [--output eval-failure-baseline.json]
```

生成 reviewed baseline JSON。这个文件用于记录“已经人工审阅并暂时接受”的历史失败 cluster，包含稳定 `cluster_key`、失败模式、规范化原因、指纹、样例 case、模型和标签分布。建议像维护安全例外一样 review、提交和定期清理。

### `init-config`

```bash
eval-failure-clusterer init-config [PATH]
```

生成可编辑的默认配置文件。

### `check`

```bash
eval-failure-clusterer check INPUT [--config config.json] [--baseline previous.jsonl] [--reviewed-baseline reviewed.json] [--output DIR] [--check warning|error]
```

适合 CI 使用：

- `warning`: 输出检查结果，进程退出码为 `0`
- `error`: 若发现失败、回归或异常，进程退出码为 `2`

`--baseline` 是 baseline/candidate 数据集对比，用来发现回归；`--reviewed-baseline` 是已审阅 cluster 例外，用来抑制历史已接受失败。两者可以同时使用。reviewed baseline 只抑制失败 cluster 门禁，不会隐藏延迟异常、成本异常或显式数据集对比回归。

典型 reviewed baseline 接入方式：

```bash
# 首次接入：生成并人工审阅
eval-failure-clusterer baseline eval-results.jsonl --output eval-failure-baseline.json

# 后续 CI：消费已提交的 reviewed baseline
eval-failure-clusterer check eval-results.jsonl \
  --reviewed-baseline eval-failure-baseline.json \
  --check error \
  --output build/eval-check
```

不要在同一个阻断型 CI run 中先生成 baseline 再消费它，否则当前失败 cluster 会被直接接受。首次接入时应生成文件、review diff、提交 baseline，然后在后续 run 中使用。

## 配置文件

`init-config` 生成的是 JSON 文件，包含：

- 字段映射
- 标签分隔符
- 失败状态和通过状态白名单
- 延迟 / 成本异常阈值
- cluster 最小相似度
- 优先级权重

## AI eval 工作流建议

1. 每次模型、prompt、检索或工具链改动后导出 eval 结果。
2. 使用 `cluster` 看失败是否集中在几类问题。
3. 使用 `sample` 给研发、prompt 工程或数据标注同学提供最小复现集。
4. 使用 `compare` 和上一个稳定版本对比，确认是否出现新回归。
5. 首次接入已有失败集时，生成 `baseline` 并人工审阅，避免历史失败阻塞所有后续改动。
6. 在 CI 中运行 `check --reviewed-baseline ... --check error`，阻止新增或未审阅失败进入主分支。

## CI 示例

```yaml
name: eval-gate
on: [push, pull_request]
permissions:
  contents: read
  security-events: write
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install .
      - run: eval-failure-clusterer check examples/eval_results.jsonl --reviewed-baseline eval-failure-baseline.json --check error --output build/eval-check
      - run: eval-failure-clusterer cluster examples/eval_results.jsonl --format sarif --output build/eval-sarif
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: build/eval-sarif/clusters.sarif
```

## 隐私与安全

- 工具默认完全离线运行。
- 不会调用 embedding、LLM 或第三方 SaaS API。
- 适合处理内部测试输出，但仍建议在导出样例前检查是否含敏感数据。
- 若需要脱敏，建议在输入前对 `output`、`expected`、`actual` 做清洗。

## 限制

- 文本聚类是启发式方法，不等价于语义 embedding 聚类。
- 对高度结构化或超短文本失败原因，字段规则归一化通常比指纹更重要。
- 延迟和成本异常是分布式阈值检测，不是严格统计检验。
- baseline compare 依赖输入字段稳定，若 case id 大量变化会降低对比精度。
- reviewed baseline 是审计文件，不是永久忽略规则；输入字段或规范化逻辑大幅变化时需要重新审阅。

## English

`eval-failure-clusterer` is an offline Python CLI for AI eval and LLM app developers. It ingests JSONL/CSV evaluation results, infers pass/fail, groups failures by normalized reason, textual fingerprint, missing fields, and latency/cost anomalies, then generates actionable reports for triage and CI gating. The project is runtime-dependency free and designed for deterministic local analysis.

Main commands:

- `cluster`
- `sample`
- `compare`
- `baseline`
- `init-config`
- `check`

Typical outputs:

- Brief triage summary for PR comments and agent handoff
- Markdown summary for humans
- JSON / CSV for downstream tooling
- JUnit XML for CI dashboards
- SARIF 2.1.0 for GitHub Code Scanning
- Reviewed baseline JSON for accepted historical failure clusters

See `examples/` for runnable sample data.

Example:

```bash
eval-failure-clusterer cluster examples/eval_results.jsonl \
  --format brief,markdown,json,csv,junit,sarif \
  --output outputs/eval-triage
```

Reviewed baseline workflow:

```bash
# Generate once, review, then commit.
eval-failure-clusterer baseline eval-results.jsonl --output eval-failure-baseline.json

# Later CI runs fail on new or unreviewed failure clusters.
eval-failure-clusterer check eval-results.jsonl \
  --reviewed-baseline eval-failure-baseline.json \
  --check error \
  --output build/eval-check
```

`--baseline` compares a previous eval dataset with a candidate dataset. `--reviewed-baseline` consumes a reviewed exception file for accepted historical failure clusters. They solve different problems and can be used together. Reviewed baselines suppress the failure-cluster gate only; latency anomalies, cost anomalies, and explicit dataset regressions remain visible.
