# 更新日志

本项目的所有重要变更都会记录在此文件中。

## [1.0.2] - 2026-11-03

### 优化

- 插件配置的下拉选项改用官方文档规定的 `options` + `subtitles` 写法；框架已挂载的工具改为在说明中标注“框架已挂载”，手动取消后会自动恢复勾选。
- `FunctionTool`、`ToolSet` 改为从公开接口 `astrbot.api` 导入。

### 修复

- 框架配置缺少字段时不再报错；读取工具、保存配置、读取会话配置失败时只记录日志，不影响插件加载和 LLM 请求。

### 文档

- README 按 AstrBot 插件常见格式重写。
- 新增 AGPL-3.0 许可证和更新日志。

## [1.0.1] - 2026-10-25

### 新增

- 框架已默认挂载的搜索和正文提取工具自动勾选并锁定，避免重复补挂载。
- 存在多份框架配置时，只锁定所有启用搜索的配置都已挂载的工具，各会话执行时分别去重。
- 插件 Logo。

## [1.0.0] - 2026-10-25

### 新增

- 首次发布：动态读取框架内置搜索工具，可多选并在 LLM 请求中同时挂载。

[1.0.2]: https://github.com/monbed/astrbot_plugin_builtin_search_mount/compare/1cab7982e9e0bd31b838c10f55078d5e469e4042...main
[1.0.1]: https://github.com/monbed/astrbot_plugin_builtin_search_mount/commit/1cab7982e9e0bd31b838c10f55078d5e469e4042
[1.0.0]: https://github.com/monbed/astrbot_plugin_builtin_search_mount/commit/aebb251bbe375fdca91acf5f8b92525fd7cd3ce9
