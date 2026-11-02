from astrbot.api import AstrBotConfig, FunctionTool, ToolSet, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star

# The builtin tool registry has no public ``astrbot.api`` wrapper yet, so it is
# imported from the core package. Requires AstrBot >= 4.28.0 (see metadata.yaml).
from astrbot.core.tools.registry import (
    get_builtin_tool_config_rule,
    get_builtin_tool_name,
    iter_builtin_tool_classes,
)

_WEB_SEARCH_KEY = "provider_settings.web_search"
_FRAMEWORK_PREFIX = "框架已挂载 · "


def _search_enabled(profile: dict) -> bool:
    """Return whether a framework profile uses the local agent with web search.

    Args:
        profile: A framework configuration profile.

    Returns:
        True when the profile runs the builtin agent and enables web search.
    """
    runner = (profile.get("agent_runner") or {}).get("runner_type")
    web_search = (profile.get("provider_settings") or {}).get("web_search")
    return runner == "local" and bool(web_search)


class Main(Star):
    """Mount manually selected native search tools alongside the default engine."""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context, config)
        self.config = config
        self._refresh_tool_options()

    def _discover_tools(self) -> tuple[dict[str, FunctionTool], set[str]]:
        """Discover registered search tools and those every profile already mounts.

        Returns:
            Native search tools indexed by name, and the names the framework
            provides in every enabled profile.
        """
        manager = self.context.get_llm_tool_manager()
        profiles = [
            profile
            for profile in self.context.astrbot_config_mgr.confs.values()
            if _search_enabled(profile)
        ]
        tools: dict[str, FunctionTool] = {}
        provided: set[str] = set()
        for tool_class in iter_builtin_tool_classes():
            name = get_builtin_tool_name(tool_class)
            rule = get_builtin_tool_config_rule(name)
            if rule is None or not any(
                condition.key == _WEB_SEARCH_KEY for condition in rule.conditions
            ):
                continue
            tools[name] = manager.get_builtin_tool(tool_class)
            if profiles and all(
                all(condition["matched"] for condition in rule.evaluate(profile))
                for profile in profiles
            ):
                provided.add(name)
        return tools, provided

    def _refresh_tool_options(self) -> dict[str, FunctionTool]:
        """Refresh the configuration choices from the framework tool registry.

        Errors are logged instead of raised so the plugin never breaks loading
        or the LLM request pipeline.

        Returns:
            Current native search tools indexed by their registered names, or an
            empty dict when discovery fails.
        """
        try:
            tools, provided = self._discover_tools()
        except Exception as exc:
            logger.error(f"读取框架内置搜索工具失败: {exc}", exc_info=True)
            return {}

        # Use the documented ``options`` + ``subtitles`` schema fields.
        names = sorted(tools)
        schema = getattr(self.config, "schema", None) or {}
        field = schema.get("tools")
        if field is not None:
            field["options"] = names
            field["subtitles"] = [
                (_FRAMEWORK_PREFIX if name in provided else "")
                + (tools[name].description or "")
                for name in names
            ]

        # The plugin selection is global; only lock tools provided everywhere.
        # Locked tools are re-added if unchecked, since the framework mounts them.
        previous = self.config.get("_framework_tools", [])
        selected = self.config.get("tools", [])
        manual = list(
            dict.fromkeys(
                name
                for name in selected
                if name not in previous and name not in provided
            )
        )
        locked = sorted(provided)
        combined = manual + locked
        if combined != selected or locked != previous:
            self.config["tools"] = combined
            self.config["_framework_tools"] = locked
            try:
                self.config.save_config()
            except Exception as exc:
                logger.warning(f"保存插件配置失败: {exc}")
        return tools

    @filter.on_llm_request()
    async def mount_search_tools(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        """Add the selected native tools to this request without copying settings.

        Args:
            event: Message whose session determines the framework configuration.
            req: Request whose existing tool pool receives the selected tools.
        """
        tools = self._refresh_tool_options()
        if not tools:
            return
        framework_tools = self.config.get("_framework_tools", [])
        selected = [
            name
            for name in self.config.get("tools", [])
            if name not in framework_tools
        ]
        if not selected:
            return

        try:
            framework_config = self.context.get_config(umo=event.unified_msg_origin)
        except Exception as exc:
            logger.warning(f"读取会话框架配置失败: {exc}")
            return
        if not framework_config or not _search_enabled(framework_config):
            return

        for name in selected:
            if req.func_tool is not None and req.func_tool.get_tool(name) is not None:
                continue

            # Native tools resolve keys from the calling session when executed.
            tool = tools.get(name)
            if tool is None or not tool.active:
                continue
            if req.func_tool is None:
                req.func_tool = ToolSet()
            req.func_tool.add_tool(tool)

    async def terminate(self) -> None:
        """Nothing to release; tools are only added per request."""
