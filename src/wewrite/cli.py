"""`wewrite` CLI 调度器 —— 把子命令分发到 commands/ 与 toolkit/ 的既有 main()。

设计约束：各命令模块保持独立 argparse（历史上是独立脚本），调度器只做
「子命令名 → 模块」映射并透传其余参数，不重复定义参数。
"""

import importlib
import sys

from . import __version__
from .paths import home

# 子命令 → (模块, 一句话说明)。模块须提供 main(argv=None) 或 main()。
_COMMANDS = {
    "diagnose": ("wewrite.commands.diagnose", "环境 + 配置自检（降级标记 JSON）"),
    "score": ("wewrite.commands.humanness_score", "写作质量评分（11 项检测）"),
    "content-eval": ("wewrite.commands.content_eval", "汇总编辑判断与初稿修改幅度"),
    "hotspots": ("wewrite.commands.fetch_hotspots", "多平台热点抓取"),
    "search-articles": ("wewrite.commands.search_articles", "搜狗微信搜索公众号文章"),
    "seo": ("wewrite.commands.seo_keywords", "SEO 关键词分析"),
    "stats": ("wewrite.commands.fetch_stats", "微信文章数据回填 history"),
    "learn-edits": ("wewrite.commands.learn_edits", "学习人工修改（diff → lessons）"),
    "learn-theme": ("wewrite.commands.learn_theme", "从公众号文章 URL 学排版主题"),
    "exemplar": ("wewrite.commands.extract_exemplar", "范文风格库（导入 / --list）"),
    "fetch-article": ("wewrite.commands.fetch_article", "公众号文章 URL → Markdown"),
    "llm-write": ("wewrite.commands.llm_write", "混合路由写作（DeepSeek 等出稿）"),
    "similarity": ("wewrite.commands.similarity_check", "多平台版本原创度检查"),
    "run": ("wewrite.commands.run_manager", "独立文章任务：开始 / 恢复 / 完成"),
    "sources": ("wewrite.commands.source_ledger", "记录文章事实来源"),
    "build-playbook": ("wewrite.commands.build_playbook", "从历史语料生成 playbook"),
    "image-gen": ("wewrite.toolkit.image_gen", "AI 图片生成（多 provider fallback）"),
    "validate": ("wewrite.commands.validate_html", "HTML 微信兼容性校验"),
}

# toolkit/cli.py 自带子命令（preview/publish/gallery/themes/image-post/learn-theme），
# 这些名字直接整体透传给它。
_TOOLKIT_PASSTHROUGH = {"preview", "publish", "gallery", "themes", "image-post"}


def _usage() -> str:
    lines = [f"wewrite {__version__} — 公众号内容管道 CLI（状态目录: {home()}）", "", "用法: wewrite <命令> [参数…]", "", "命令:"]
    for name, (_, desc) in _COMMANDS.items():
        lines.append(f"  {name:<16}{desc}")
    for name in sorted(_TOOLKIT_PASSTHROUGH):
        lines.append(f"  {name:<16}排版工具链（toolkit）")
    lines += [
        "  home            输出状态目录路径",
        "  migrate         迁移旧版仓库内状态到状态目录",
        "",
        "任意命令加 --help 看详细参数。",
    ]
    return "\n".join(lines)


def main() -> None:
    argv = sys.argv[1:]
    if not argv or argv[0] in {"-h", "--help"}:
        print(_usage())
        return
    if argv[0] in {"-V", "--version"}:
        print(__version__)
        return

    cmd, rest = argv[0], argv[1:]

    if cmd == "home":
        print(home())
        return
    if cmd == "migrate":
        from .migrate import main as migrate_main
        migrate_main(rest)
        return
    if cmd in _TOOLKIT_PASSTHROUGH:
        from .toolkit import cli as toolkit_cli
        sys.argv = ["wewrite", cmd, *rest]
        toolkit_cli.main()
        return
    if cmd in _COMMANDS:
        module_name, _ = _COMMANDS[cmd]
        module = importlib.import_module(module_name)
        sys.argv = [f"wewrite {cmd}", *rest]
        module.main()
        return

    print(f"未知命令: {cmd}\n\n{_usage()}", file=sys.stderr)
    sys.exit(2)
