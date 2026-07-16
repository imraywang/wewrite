#!/usr/bin/env python3
"""混合路由写作工具：把「内容生成」从编排 agent 卸载到便宜的写作模型（默认 DeepSeek）。

为什么存在：整条管道由 Claude 当编排（conductor），但长文中文生成交给更便宜、中文更像人的
写作模型。关键省钱点——**正文走 文件→文件，stdout 只回简短摘要**，绝不把大段正文回灌编排
agent 的上下文（编排成本的大头是逐轮重发的滚雪球上下文）。

用法（编排 agent 通过 Bash 调用）：
    wewrite llm-write --brief runs/<run_id>/brief.md --output runs/<run_id>/article.md
    wewrite llm-write --brief runs/<run_id>/brief.md --output runs/<run_id>/xiaohongshu.md --system-extra "小红书口吻…"

brief 文件由编排 agent 写好：选题 / 框架 / **真实素材锚点** / 人格 / 目标字数 / （重写时的）定向修改指令。
编辑质量底线由本工具的 system prompt 注入，并与 skill 的编辑质量标准保持一致。

退出码（供 SKILL.md 分支降级）：
    0 成功；3 未配置写作模型（→ 降级为 agent 自写）；4 调用失败（→ 降级或重试）。

配置（环境变量）：
    WEWRITE_WRITER_API_KEY      写作模型 key（缺省则退出码 3）
    WEWRITE_WRITER_PROVIDER     deepseek|openai|…（默认 deepseek，仅作标识；走 OpenAI 兼容协议）
    WEWRITE_WRITER_BASE_URL     默认 https://api.deepseek.com
    WEWRITE_WRITER_MODEL        默认 deepseek-chat
    WEWRITE_WRITER_TEMPERATURE  默认 1.0（保留表达变化，但别太高以免编造事实）
    WEWRITE_WRITER_MAX_TOKENS   默认 4000
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ANTI_AI_FALLBACK = """你是资深中文公众号编辑。只使用 brief 提供的事实、数据、案例和个人经历，绝不补写未提供的亲历、数字、引述或身份。明确区分事实、推断和个人意见。文章要有清楚的核心判断、对读者有用的具体内容，并符合 brief 给出的账号声音。语言直接自然，删除套话、重复和无效标题；不要为了显得像人而刻意制造碎句、负面情绪、网络黑话或离题段落。"""

# API 模式专属的输出格式约束（内联自写不需要——它走 Write 工具直接落 markdown 文件）。
_OUTPUT_FORMAT = "\n\n只输出正文（含一个口语化标题），不要任何前后说明，不要用代码块包裹。"


def _anti_ai_system() -> str:
    """Load the packaged editorial contract, with a safe fallback."""
    pkg_data = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "data", "anti-ai-writing-system.md")
    try:
        with open(pkg_data, encoding="utf-8") as f:
            return f.read().strip() + _OUTPUT_FORMAT
    except OSError:
        return _ANTI_AI_FALLBACK + _OUTPUT_FORMAT


def _load_config() -> dict:
    key = os.environ.get("WEWRITE_WRITER_API_KEY", "").strip()
    if not key:
        print("WRITER_NOT_CONFIGURED: 未配置 WEWRITE_WRITER_API_KEY", file=sys.stderr)
        sys.exit(3)
    return {
        "provider": os.environ.get("WEWRITE_WRITER_PROVIDER", "deepseek"),
        "key": key,
        "base_url": os.environ.get("WEWRITE_WRITER_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        "model": os.environ.get("WEWRITE_WRITER_MODEL", "deepseek-chat"),
        "temperature": float(os.environ.get("WEWRITE_WRITER_TEMPERATURE", "1.0")),
        "max_tokens": int(os.environ.get("WEWRITE_WRITER_MAX_TOKENS", "4000")),
    }


def call_writer(cfg: dict, system: str, user: str) -> tuple[str, dict]:
    """调 OpenAI 兼容的 /chat/completions（DeepSeek / OpenAI 同构）。返回 (正文, usage)。"""
    import requests  # 容器/服务器内有；本地拦截环境只在真调时才 import

    resp = requests.post(
        cfg["base_url"] + "/chat/completions",
        headers={"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"},
        json={
            "model": cfg["model"],
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": cfg["temperature"],
            "max_tokens": cfg["max_tokens"],
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("\n", 1)
        text = parts[1] if len(parts) > 1 else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="混合路由写作工具（DeepSeek 等写作模型出稿）")
    ap.add_argument("--brief", required=True, help="brief 文件路径（编排 agent 写好）")
    ap.add_argument("--output", required=True, help="正文输出文件路径")
    ap.add_argument("--system-extra", default="", help="追加编辑要求（如平台口吻）")
    args = ap.parse_args(argv)

    cfg = _load_config()
    with open(args.brief, encoding="utf-8") as f:
        brief = f.read()
    system = _anti_ai_system() + (("\n\n" + args.system_extra) if args.system_extra else "")

    try:
        content, usage = call_writer(cfg, system, brief)
    except Exception as exc:  # noqa: BLE001 - 失败给独立退出码，SKILL.md 据此降级
        print(f"WRITER_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(4)

    content = _strip_code_fence(content)
    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content + "\n")

    # 只回摘要，不回正文 —— 保住「不灌编排上下文」的省钱命门
    print(json.dumps({
        "ok": True, "output": args.output, "chars": len(content), "model": cfg["model"],
        "tokens_in": usage.get("prompt_tokens"), "tokens_out": usage.get("completion_tokens"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
