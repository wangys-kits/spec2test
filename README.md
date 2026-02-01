# spec2ir-demo

一个从人类 Spec (YAML) 到 Test IR (YAML) 的端到端示例，包含：

- Playwright 捕获 **A11y 可访问性树**，帮助生成鲁棒 locator。
- 可插拔 LLM Provider（Mock / OpenAI 兼容），支持流式输出。
- 严格的 IR Schema 校验（Pydantic）。
- `spec2ir_runner`：基于 Playwright 的 IR 执行器，可直接在浏览器里验证步骤。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e .
python -m playwright install
```

> 建议将密钥、账号等写入 `.env`，仓库在启动 CLI 时会自动 `load_dotenv`。

## 生成 IR（spec2ir CLI）

### Mock provider（离线）

This captures a11y tree from the target URL and outputs a deterministic demo IR.

```bash
spec2ir --spec specs/waf_login_1.yaml --provider mock --capture-a11y --out specs/waf_login_1.ir.yaml
```

### OpenAI 兼容 LLM

`.env` 或环境中需要包含：

```bash
export LLM_BASE_URL="https://your-llm-gateway/v1"
export LLM_API_KEY="xxxxx"
export LLM_MODEL="your-model"
# 可选：LLM_STREAM=1 开启流式输出
```

```bash
spec2ir --spec specs/waf_login_1.yaml --provider openai_compat --capture-a11y --out specs/waf_login_1.ir.yaml
```

### 常用参数

- `--capture-a11y`：使用 Playwright 抓取 a11y tree，LLM 会据此选择更稳定的 locator。
- `SPEC2IR_HEADLESS=0`：生成 IR 或执行 IR 时若需可视化浏览器，可设置为 0。
- `.env` 中的 `${ADMIN_USER}` / `${ADMIN_PASS}` 会在 runner 中自动替换。

## 执行 IR（spec2ir_runner CLI）

将生成的 IR 投入 runner，可直接驱动 Playwright 验证：

```bash
SPEC2IR_HEADLESS=0 python -m spec2ir_runner.main --ir specs/waf_login_1.ir.yaml
```

runner 会：

1. 读取 `.env` 并替换 `${VAR}` 占位符。
2. 依次执行 `goto/fill/click/wait_for`。
3. 根据 `expects` 断言（例如 `url_is`、`visible_text`）。

## 约定与注意事项

- **No raw secrets**: any `fill.value` should be variables like `${ADMIN_USER}` `${ADMIN_PASS}`.
- Locator preference: `testid > role+name > label > text > css/xpath`。
- `wait_for`/`url_is` 应尽量用 path 或 glob（如 `**/statistics*`）以兼容 hash/参数。
- `SPEC2IR_HEADLESS` 同时作用于 spec2ir 与 spec2ir_runner。

## 目录

- `specs/` sample spec + generated IR
- `src/spec2ir/ui_context.py` a11y capture via Playwright
- `src/spec2ir/llm/` pluggable LLM providers
- `src/spec2ir_runner/` Playwright 执行器
