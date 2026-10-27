from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .agent_workflow import AgentWorkflow, verify_existing
from .healing import propose_healing
from .hub import QualityHub
from .models import load_json, validate_spec
from .onboarding import onboard_project
from .orchestrator import Orchestrator
from .project_memory import ProjectMemory
from .report import chinese_value, generate_report
from .runner import run_pytest
from .triage import triage_run

ROOT = Path(__file__).resolve().parent.parent

GUIDE = """QualityOS 中文使用导航

主入口：让真实 Agent 操作你的项目（不是 fixture 演示）

1. 先启动你的测试环境，再给它地址和需求文档
   .venv/Scripts/python -m quality_os.cli auto --url http://127.0.0.1:8765 --document specs/refund-prd.md --run-id my-project

2. Agent 会自动完成
   浏览器探索 → 独立风险挑战 → Playwright 测试生成 → 独立执行 → 证据修复 → 最终重跑

3. 打开结果
   artifacts/agent-runs/my-project/report.html
   通过也只进入人工审批，不会自动合并候选。

旧命令定位
- run：内置退款 legacy 编排演示。
- onboard：只生成静态规格/用例草案，不操作应用。
- eval：检查工作流自身门禁。

所有 auto 阶段都真实调用 Kimi 和 Playwright MCP，会消耗 token；只连接隔离测试环境。
"""

SUMMARY_LABELS = {
    "workflow_status": "工作流状态",
    "provider": "模型提供方",
    "ai_generation_used": "是否使用真实 AI",
    "baseline": "正确版本基线",
    "faults_caught": "注入故障检出",
    "human_approval": "人工审批",
    "provider_duration_ms": "模型调用耗时（毫秒）",
    "model_cost": "模型费用",
    "human_review_time": "人工审查耗时",
    "cost_per_accepted_test": "每条验收测试成本",
    "false_green_claimed": "是否宣称假绿",
    "next_step": "下一步",
}


class ChineseArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "可选参数"
        if self._actions and isinstance(self._actions[0], argparse._HelpAction):
            self._actions[0].help = "显示帮助并退出"

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "用法：", 1)

    def format_help(self) -> str:
        return super().format_help().replace("usage:", "用法：", 1)

    def error(self, message: str) -> None:
        translations = {
            "the following arguments are required:": "缺少必填参数：",
            "invalid choice:": "无效的选项值：",
            "unrecognized arguments:": "无法识别的参数：",
            "expected one argument": "该参数需要一个值",
        }
        for source, target in translations.items():
            message = message.replace(source, target)
        self.print_usage(sys.stderr)
        self.exit(2, f"参数错误：{message}\n可运行 guide 查看中文使用导航。\n")


def print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> ChineseArgumentParser:
    parser = ChineseArgumentParser(prog="quality-os", description="真实 Agent 驱动、证据闭环的 AI 自动化测试工作流；运行 guide 查看中文导航")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}", help="显示当前版本号")
    subparsers = parser.add_subparsers(dest="command", title="可用命令")

    auto = subparsers.add_parser("auto", help="真实 Agent 自主探索、生成并执行 Playwright 测试")
    auto.add_argument("--url", required=True, help="已经启动的测试环境地址")
    auto.add_argument("--document", type=Path, action="append", required=True, help="需求/接口文档；可重复传入")
    auto.add_argument("--project-dir", type=Path, help="可选项目源码目录，仅作为只读上下文")
    auto.add_argument("--run-id", required=True, help="新运行标识，证据保存到 artifacts/agent-runs/<标识>")
    auto.add_argument("--browser", choices=["msedge", "chrome", "firefox", "webkit"], default="msedge", help="Playwright 浏览器（默认：msedge）")
    auto.add_argument("--timeout", type=int, default=1200, help="每个 Agent 阶段超时秒数（默认：1200）")
    auto.add_argument("--model", default="kimi-code/k3.1-pro-highspeed", help="真实 Kimi 模型别名；默认使用高速模型")
    auto.add_argument("--project-key", help="项目质量记忆标识；默认使用 run-id")
    auto.add_argument("--fault-url", action="append", default=[], metavar="名称=URL", help="可选故障环境；候选测试必须在该环境失败")
    auto.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)

    regression = subparsers.add_parser("regress", help="复用项目质量记忆，独立重跑最近候选测试")
    regression.add_argument("--project-key", required=True, help="auto 时使用的项目标识")
    regression.add_argument("--run-id", required=True, help="本次回归的新运行标识")
    regression.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)

    verify = subparsers.add_parser("verify", help="复用已有候选，独立执行验收，不重复消耗生成 token")
    verify.add_argument("--run-dir", type=Path, required=True, help="已有 artifacts/agent-runs/<标识> 目录")
    verify.add_argument("--heal", action="store_true", help="失败后调用真实 Agent 修复候选，再独立重跑")

    run = subparsers.add_parser("run", help="旧版内置退款编排演示（legacy），不是通用 Agent 主入口")
    run.add_argument("--provider", choices=["fixture", "kimi", "claude"], default="kimi", help="模型提供方；fixture 是明确标注的离线样本，不是 AI（默认：kimi）")
    run.add_argument("--run-id", default="demo", help="本次运行标识，证据保存在 artifacts/runs/<标识>/")
    run.add_argument("--resume", action="store_true", help="从断点继续，复用已通过阶段的产物")
    run.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)

    onboard = subparsers.add_parser("onboard", help="读取你的 PRD/接口文档，用真实模型生成候选规格和用例")
    onboard.add_argument("--document", type=Path, action="append", required=True, help="需求或接口文档路径；可重复传入多个文档")
    onboard.add_argument("--output-dir", type=Path, required=True, help="独立候选资产输出目录")
    onboard.add_argument("--provider", choices=["kimi", "claude"], default="kimi", help="真实模型提供方（默认：kimi）")
    onboard.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)

    subparsers.add_parser("guide", help="查看中文使用导航和下一步")

    validate = subparsers.add_parser("validate-spec", help="按确定性门禁校验规格，不调用模型")
    validate.add_argument("--spec", type=Path, required=True, help="待校验的规格 JSON")
    validate.add_argument("--policy", type=Path, default=ROOT / "policies" / "gates.json", help="门禁策略路径")

    triage = subparsers.add_parser("triage", help="对保留的首次失败进行分类")
    triage.add_argument("--run-dir", type=Path, required=True, help="包含 run.json 和 junit.xml 的执行证据目录")

    heal = subparsers.add_parser("heal", help="观察或提交仅限定位器的修复候选，不自动合并")
    heal.add_argument("--source", type=Path, required=True, help="原始测试文件")
    heal.add_argument("--output-dir", type=Path, required=True, help="独立候选输出目录")
    heal.add_argument("--old", required=True, help="旧定位器文本")
    heal.add_argument("--new", required=True, help="新定位器文本")
    heal.add_argument("--mode", choices=["observe", "propose"], default="observe", help="observe 仅检查；propose 生成待人工审核候选")

    report = subparsers.add_parser("report", help="根据已有证据重新生成质量报告")
    report.add_argument("--run-dir", type=Path, required=True, help="运行证据目录")

    trace = subparsers.add_parser("trace", help="追溯需求关联的风险、用例、测试和运行")
    trace.add_argument("--run-dir", type=Path, required=True, help="运行证据目录")
    trace.add_argument("--requirement", required=True, help="需求 ID")

    browser = subparsers.add_parser("browser", help="运行真实浏览器测试并保存截图和 Trace")
    browser.add_argument("--test-path", type=Path, default=ROOT / "tests" / "e2e" / "test_refund_ui.py", help="浏览器测试文件")
    browser.add_argument("--run-dir", type=Path, default=ROOT / "artifacts" / "browser", help="证据输出目录")
    browser.add_argument("--faults", default="", help="逗号分隔的演示故障开关")
    browser.add_argument("--ui-version", choices=["v1", "v2"], default="v1", help="演示页面版本")
    browser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)

    evaluate = subparsers.add_parser("eval", help="运行工作流自身的确定性黄金评测，不调用模型")
    evaluate.add_argument("--output-dir", type=Path, default=ROOT / "artifacts" / "evals", help="评测报告输出目录")
    evaluate.add_argument("--trials", type=int, default=3, help="每个任务重复次数（默认：3）")
    evaluate.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command in {None, "guide"}:
        print(GUIDE)
        return
    try:
        if args.command == "auto":
            run_dir = args.root.resolve() / "artifacts" / "agent-runs" / args.run_id
            if any("=" not in item or not item.split("=", 1)[0] for item in args.fault_url):
                raise ValueError("--fault-url 格式必须是 故障名称=URL。")
            fault_targets = dict(item.split("=", 1) for item in args.fault_url)
            print("启动真实 AI 自动化测试：Agent 将实际使用 Playwright CLI + Skill，不会读取预制测试答案。")
            result = AgentWorkflow(
                run_dir, args.url, args.document, args.project_dir, args.browser, args.timeout,
                project_key=args.project_key or args.run_id, fault_targets=fault_targets, model=args.model,
            ).run()
            print(f"工作流状态：{result['status']}")
            print(f"中文报告：{run_dir / 'report.html'}")
            print(f"候选测试：{run_dir / 'workspace' / 'tests' / 'candidates'}")
            print(f"项目记忆：{args.root.resolve() / 'artifacts' / 'projects' / (args.project_key or args.run_id)}")
            if result["status"] != "pending_human_approval":
                print(f"未通过：{result['error']}", file=sys.stderr)
                sys.exit(1)
        elif args.command == "verify":
            result = verify_existing(args.run_dir.resolve(), args.heal)
            print(f"独立验收状态：{result['status']}")
            print(f"中文报告：{args.run_dir.resolve() / 'report.html'}")
            if result["status"] != "pending_human_approval":
                print(f"未通过：{result['error']}", file=sys.stderr)
                sys.exit(1)
        elif args.command == "regress":
            run_dir = args.root.resolve() / "artifacts" / "agent-runs" / args.run_id
            result = ProjectMemory(args.root.resolve(), args.project_key).regression(run_dir)
            print(f"回归状态：{result['status']}；{result['comparison']}")
            print(f"中文报告：{run_dir / 'report.html'}")
            if result["status"] != "pending_human_approval":
                sys.exit(1)
        elif args.command == "run":
            run_dir = args.root.resolve() / "artifacts" / "runs" / args.run_id
            print(f"开始运行：{args.run_id}；提供方：{args.provider}。")
            if args.provider == "fixture":
                print("当前是离线样本模式，不会调用大模型，报告会保留 ai_generation_used=false。")
            else:
                print(f"将真实调用 {args.provider} 完成规划、测试生成和独立审查，请保持账号与网络可用。")
            result = Orchestrator(args.root.resolve(), run_dir, args.provider, args.resume).run()
            for key, value in result["report"]["summary"].items():
                print(f"{SUMMARY_LABELS.get(key, key)}：{chinese_value(value)}")
            print(f"\nHTML 报告：{result['report']['html']}")
            print("下一步：打开报告核对证据，由命名审核人处理人工审批；系统不会自动合并候选。")
        elif args.command == "onboard":
            print(f"正在读取 {len(args.document)} 份文档并真实调用 {args.provider}，生成候选项目资产……")
            result = onboard_project(args.root.resolve(), args.document, args.output_dir.resolve(), args.provider)
            print(f"草案已生成：{args.output_dir.resolve() / 'onboarding.md'}")
            print(f"候选需求 {result['requirement_count']} 条，候选用例 {result['case_count']} 条；测试尚未执行。")
            print("下一步：逐条解决待确认问题，由真实业务负责人填写 approved_by；不要直接合并草案。")
        elif args.command == "validate-spec":
            issues = validate_spec(load_json(args.spec), load_json(args.policy))
            print_json({"passed": not issues, "issues": issues})
            print("校验通过：可以进入后续测试设计。" if not issues else "校验未通过：请先解决上述问题，不能用模型回答替代业务批准。")
            sys.exit(1 if issues else 0)
        elif args.command == "triage":
            print_json(triage_run(args.run_dir))
        elif args.command == "heal":
            result = propose_healing(args.source, args.output_dir, args.old, args.new, args.mode)
            print_json(result)
            print("下一步：候选仍需定向重跑、回归和命名审核人批准，不会自动合并。")
        elif args.command == "report":
            result = generate_report(args.run_dir)
            print(f"报告已生成：{result['html']}")
        elif args.command == "trace":
            hub = QualityHub(args.run_dir / "quality-hub.db")
            try:
                print_json(hub.trace_requirement(args.requirement))
            finally:
                hub.close()
        elif args.command == "eval":
            from .workflow_eval import run_workflow_evals
            result = run_workflow_evals(args.root.resolve(), args.output_dir.resolve(), args.trials)
            print_json({key: value for key, value in result.items() if key != "results"})
            print(f"评测报告：{args.output_dir.resolve() / 'workflow-evals.md'}")
            sys.exit(0 if result["passed"] else 1)
        elif args.command == "browser":
            result = run_pytest(args.root.resolve(), args.test_path.resolve(), args.run_dir.resolve(), "browser", set(filter(None, args.faults.split(","))), args.ui_version)
            print_json(result.to_dict())
            print(f"执行状态：{'通过' if result.exit_code == 0 else '失败'}；证据目录：{result.evidence_dir}")
            sys.exit(result.exit_code)
    except KeyboardInterrupt:
        print("\n已由用户中止；已生成的证据仍保留在磁盘。", file=sys.stderr)
        sys.exit(130)
    except Exception as error:
        print(f"\n执行被阻断：{error}", file=sys.stderr)
        if args.command == "run":
            report_path = args.root.resolve() / "artifacts" / "runs" / args.run_id / "report.html"
            if report_path.exists():
                print(f"失败证据报告：{report_path}", file=sys.stderr)
            print("下一步：根据失败阶段修复输入或模型配置后，加 --resume 从断点重跑；不会自动改用 fixture。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
