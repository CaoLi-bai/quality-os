from .base import GenerationResult, Provider
from .cli import CLIProvider
from .fixture import FixtureProvider


def create_provider(name: str, root):
    if name == "fixture":
        return FixtureProvider(root)
    if name in {"kimi", "claude"}:
        return CLIProvider(name)
    raise ValueError(f"未知模型提供方：{name}。可选值为 fixture、kimi、claude。")


__all__ = ["GenerationResult", "Provider", "FixtureProvider", "CLIProvider", "create_provider"]
