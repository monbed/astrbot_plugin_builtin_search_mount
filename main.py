from astrbot.api import AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star
from astrbot.core.agent.tool import FunctionTool, ToolSet
from astrbot.core.tools.registry import (
    get_builtin_tool_config_rule,
    get_builtin_tool_name,
    iter_builtin_tool_classes,
)


class Main(Star):
    """Mount manually selected native search tools alongside the default engine."""

    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context, config)
        self.config = config
        self._refresh_tool_options()

    def _refresh_tool_options(self) -> dict[str, FunctionTool]:
        """Discover registered search tools and refresh their configuration choices.

        Returns:
            Current native search tools indexed by their registered names.
        """
        manager = self.context.get_llm_tool_manager()
        profiles = [
            profile
            for profile in self.context.astrbot_config_mgr.confs.values()
            if profile["agent_runner"]["runner_type"] == "local"
            and profile["provider_settings"]["web_search"]
        ]
        tools = {}
        provided = set()
        for tool_class in iter_builtin_tool_classes():
            name = get_builtin_tool_name(tool_class)
            rule = get_builtin_tool_config_rule(name)
            if rule is None or not any(
                condition.key == "provider_settings.web_search"
                for condition in rule.conditions
            ):
                continue
            tools[name] = manager.get_builtin_tool(tool_class)
            if profiles and all(
                all(condition["matched"] for condition in rule.evaluate(profile))
                for profile in profiles
            ):
                provided.add(name)

        # The plugin selection is global; only lock tools provided everywhere.
        names = sorted(tools)
        field = self.config.schema["tools"]
        field["options"] = [
            {
                "title": name,
                "value": name,
                "props": {
                    "disabled": name in provided,
                    "subtitle": (
                        "框架已挂载 · " + tools[name].description
                        if name in provided
                        else tools[name].description
                    ),
                },
            }
            for name in names
        ]

        previous = self.config.get("_framework_tools", [])
        selected = self.config.get("tools", [])
        manual = list(
            dict.fromkeys(
                name
                for name in selected
                if name not in previous and name not in provided
            )
        )
        combined = manual + sorted(provided)
        locked = sorted(provided)
        if combined != selected or locked != previous:
            self.config["tools"] = combined
            self.config["_framework_tools"] = locked
            self.config.save_config()
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
        selected = [
            name
            for name in self.config.get("tools", [])
            if name not in self.config.get("_framework_tools", [])
        ]
        if not selected:
            return

        framework_config = self.context.get_config(umo=event.unified_msg_origin)
        if framework_config["agent_runner"]["runner_type"] != "local":
            return
        if not framework_config["provider_settings"]["web_search"]:
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
