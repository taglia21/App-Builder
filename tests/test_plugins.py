"""Tests for the Plugin architecture."""

from src.plugins.base import PluginBase
from src.plugins.registry import PluginRegistry


class _CounterPlugin(PluginBase):
    """Test plugin that counts hook invocations."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    def on_pipeline_start(self, build_id: str, config: dict) -> None:
        self.calls["on_pipeline_start"] = self.calls.get("on_pipeline_start", 0) + 1

    def on_stage_complete(self, build_id: str, stage: str, duration_ms: float) -> None:
        self.calls["on_stage_complete"] = self.calls.get("on_stage_complete", 0) + 1

    def on_pipeline_complete(self, build_id: str, output_path=None, total_duration_ms: float = 0) -> None:
        self.calls["on_pipeline_complete"] = self.calls.get("on_pipeline_complete", 0) + 1

    def on_error(self, build_id: str, error: Exception) -> None:
        self.calls["on_error"] = self.calls.get("on_error", 0) + 1


class TestPluginRegistry:
    def test_register_and_call(self) -> None:
        reg = PluginRegistry()
        plugin = _CounterPlugin()
        reg.register(plugin)

        reg.call_hook("on_pipeline_start", build_id="b1", config={})
        reg.call_hook("on_stage_complete", build_id="b1", stage="ideas", duration_ms=100)
        reg.call_hook("on_pipeline_complete", build_id="b1", output_path="/out", total_duration_ms=5000)

        assert plugin.calls["on_pipeline_start"] == 1
        assert plugin.calls["on_stage_complete"] == 1
        assert plugin.calls["on_pipeline_complete"] == 1

    def test_call_hook_unknown_name(self) -> None:
        reg = PluginRegistry()
        plugin = _CounterPlugin()
        reg.register(plugin)
        # Should not raise
        reg.call_hook("nonexistent_hook", build_id="b1")

    def test_error_isolation(self) -> None:
        reg = PluginRegistry()

        class _BrokenPlugin(PluginBase):
            def on_pipeline_start(self, build_id: str, config: dict) -> None:
                raise RuntimeError("broken")

        ok_plugin = _CounterPlugin()
        reg.register(_BrokenPlugin())
        reg.register(ok_plugin)

        # Should not raise despite first plugin error
        reg.call_hook("on_pipeline_start", build_id="b1", config={})
        assert ok_plugin.calls.get("on_pipeline_start") == 1


class TestRegisterDecorator:
    def test_decorator_registers(self) -> None:
        # The decorator adds to the global registry; just verify the class is returned
        import src.plugins.example_plugin  # noqa: F401, E402, I001

        from src.plugins.registry import plugin_registry  # noqa: E402

        names = [p.name for p in plugin_registry._plugins]
        assert "ExamplePlugin" in names


class TestPluginBaseDefaults:
    def test_default_hooks_are_noop(self) -> None:
        class _Minimal(PluginBase):
            pass

        p = _Minimal()
        # None of these should raise
        p.on_pipeline_start(build_id="b1", config={})
        p.on_stage_complete(build_id="b1", stage="s", duration_ms=0)
        p.on_pipeline_complete(build_id="b1", output_path=None, total_duration_ms=0)
        p.on_error(build_id="b1", error=RuntimeError("x"))

    def test_name_defaults_to_class(self) -> None:
        class _MyPlugin(PluginBase):
            pass

        assert _MyPlugin().name == "_MyPlugin"
