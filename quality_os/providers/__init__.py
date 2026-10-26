from .base import GenerationResult, Provider
from .cli import CLIProvider
from .fixture import FixtureProvider


def create_provider(name: str, root):
    if name == "fixture":
        return FixtureProvider(root)
    if name in {"kimi", "claude"}:
        return CLIProvider(name)
    raise ValueError(f"Unknown provider: {name}")


__all__ = ["GenerationResult", "Provider", "FixtureProvider", "CLIProvider", "create_provider"]
