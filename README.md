# 内置搜索多工具挂载 (astrbot_plugin_builtin_search_mount)

让 AstrBot 在同一次 LLM 请求中同时挂载多个**框架内置**搜索工具，突破“网页搜索提供商”只能单选的限制。

## 功能特性

- **多引擎同时挂载**：在默认搜索引擎之外，按需补挂载 Exa、Tavily 等其他内置搜索 / 正文提取工具。
- **自动发现工具**：动态读取框架内置工具注册表，新增的搜索工具无需修改插件即可出现在选项中。
- **复用框架实现**：工具实例、API Key、Key 轮询、错误处理和返回格式全部使用 AstrBot 原生实现，插件不保存任何 Key。
- **自动去重**：框架已挂载的工具自动勾选并标注“框架已挂载”，不会重复加入。
- **按会话生效**：遵循当前会话绑定的框架配置，关闭网页搜索或不使用内置 AI 时不做任何改动。

## 环境要求

| 依赖 | 版本要求 | 说明 |
| --- | --- | --- |
| AstrBot | >= 4.28.0 | 依赖该版本引入的 `agent_runner.runner_type` 配置结构和内置工具注册表 |
| 执行方式 | AstrBot 内置 AI | 不支持 Dify、Coze 等第三方 Agent 执行器 |

**平台支持**：全平台（不依赖消息平台）。无额外 Python 依赖。

## 安装

1. 在 AstrBot 插件页面右下角点击加号，选择从链接安装，输入：

   ```text
   https://github.com/monbed/astrbot_plugin_builtin_search_mount
   ```

2. 或将整个插件目录放入 AstrBot 的 `data/plugins/` 下，然后重启 AstrBot。

## 配置

### 前置条件

1. 在会话实际使用的框架配置中，将执行方式设为“AstrBot 内置 AI”。
2. 在 `AI → 能力 → 网页搜索` 中开启“启用网页搜索”，提供商保留一个常用引擎。
3. 把需要额外使用的引擎 API Key 也保存到**同一份**框架配置中（可临时切换提供商填写并保存，再切回常用引擎；也可以直接编辑配置 JSON）。

### 插件配置项

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| 同时挂载的内置搜索工具 | 多选需要补挂载的内置工具。选项和说明自动从框架读取，框架已挂载的工具会自动勾选并标注“框架已挂载” | `[]` |

## 使用示例

### 同时使用 Tavily 与 Exa

在框架配置的 `provider_settings` 中合并以下字段（保留其他已有字段）：

```json
{
  "web_search": true,
  "websearch_provider": "tavily",
  "websearch_tavily_key": ["你的 Tavily Key"],
  "websearch_exa_key": ["你的 Exa Key"]
}
```

框架已默认挂载 Tavily，插件设置中只需再勾选 `web_search_exa`（如需 Exa 正文提取，可另外勾选 `exa_get_contents`）。

之后在对话中明确提出要求即可，例如：

```text
分别使用 Tavily 和 Exa 搜索这个问题，再交叉核对结果。
```

> 挂载只代表模型**可以**使用这些工具，是否调用、调用几次仍由模型决定。

## 工作原理

- 插件在 `on_llm_request` 钩子中通过框架的 `get_builtin_tool()` 获取原生工具实例，加入当前请求的工具集。
- 工具执行时由框架按当前会话读取 API Key 等设置；Key 缺失、无效或额度不足时，直接返回内置工具原有的错误信息。
- 工具池中已存在同名工具时保留原实例，不改写工具名称、Schema、描述或启用状态，也不会删除框架或其他插件已加入的工具。
- 插件启动时和每次 LLM 请求时都会刷新工具列表：框架新增的工具默认不勾选，已删除的工具会被跳过。

## 注意事项

- **多份框架配置**：插件的选择是全局的，只有在所有启用搜索的配置中都已挂载的工具才会被锁定为“框架已挂载”。例如配置 A 默认 Tavily、配置 B 默认 Exa，同时勾选两者后，A 只补挂载 Exa，B 只补挂载 Tavily。
- **锁定项**：标注“框架已挂载”的工具即使手动取消，也会在下次刷新时自动恢复勾选，实际挂载仍由框架负责。
- **界面显示**：框架的提供商下拉框仍是单选，内置工具页的启用标签也只反映框架原配置；补挂载是否生效以实际请求的工具池和调用记录为准。
- 插件不会根据已保存的 Key 自动挂载引擎，也不会自动勾选正文提取工具。

## 目录结构

```text
astrbot_plugin_builtin_search_mount/
├── main.py              # 插件逻辑
├── _conf_schema.json    # 插件配置定义
├── metadata.yaml        # 插件元信息
├── logo.png
├── README.md
└── LICENSE              # AGPL-3.0 许可证
```

## 相关链接

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [AstrBot 网页搜索文档](https://docs.astrbot.app/use/websearch.html)
- [AstrBot 4.28.0 发布说明](https://github.com/AstrBotDevs/AstrBot/blob/v4.28.0/changelogs/v4.28.0.md)

## 更新日志

### v1.0.2 (2026-11-03)

- 优化：插件配置的下拉选项改用官方文档规定的 `options` + `subtitles` 写法；框架已挂载的工具改为在说明中标注“框架已挂载”，手动取消后会自动恢复勾选。
- 优化：`FunctionTool`、`ToolSet` 改为从公开接口 `astrbot.api` 导入。
- 修复：框架配置缺少字段时不再报错，读取工具、保存配置、读取会话配置失败时只记录日志，不影响插件加载和 LLM 请求。
- 文档：README 按 AstrBot 插件常见格式重写，新增 AGPL-3.0 许可证。

### v1.0.1 (2026-10-25)

- 新增：框架已默认挂载的搜索和正文提取工具自动勾选并锁定，避免重复补挂载。
- 新增：存在多份框架配置时，只锁定所有启用搜索的配置都已挂载的工具，各会话执行时分别去重。
- 新增：插件 Logo。

### v1.0.0 (2026-10-25)

- 首次发布：动态读取框架内置搜索工具，可多选并在 LLM 请求中同时挂载。

## 许可证

本项目基于 [GNU Affero General Public License v3.0](LICENSE) 开源。
