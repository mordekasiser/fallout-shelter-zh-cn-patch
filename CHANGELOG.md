# 变更记录

本文件记录项目中值得关注的变化。

格式参考 Keep a Changelog，按 Added、Changed、Fixed、Security 等类别整理。

## v0.1.2-alpha - 2026-07-07

### Changed

- README 高级命令说明改为优先推荐 `generate_patch.ps1 -GameDir`，并补充底层 `tools.build_patch` 在非默认游戏目录下需要同时传 `--bundle` 和 `--game-dir`。

### Fixed

- 修复一键生成脚本在 `py -3.11` 不可用、但系统已有 Python 3.13/3.14 时可能提前报 “No suitable Python runtime found” 的问题。
- Python 启动器探测现在只接受真实可执行文件，避免函数或别名遮蔽 `py` / `python` 造成误判。
- 补充 PowerShell 回归测试，覆盖精确版本候选失败后继续尝试后续 Python 候选的场景。

## v0.1.1-alpha - 2026-06-25

### Added

- 归档 `v0.1.1-alpha` 发布说明。
- 添加用于 Python 测试套件的 GitHub Actions CI。
- 添加项目状态文档，记录治理配置、CI、分支规则、打开事项和维护说明。
- 补充安全报告、Pull Request 审查、代码所有权、依赖更新、变更记录和社区行为准则等仓库治理文件。
- 添加维护者说明，记录 `master` ruleset、更新流程、生成产物检查和 GitHub 中文评论编码要求。
- 补充一键补丁生成路径的 PowerShell 回归测试。

### Changed

- 将 GitHub Issue 模板改为中文字段，避免浏览器翻译造成字段含义不自然。
- 说明推荐下载路径，以及生成后的 `data.unity3d` 为什么会明显大于官方资源包。
- 调整 `v0.1.1-alpha` 发布说明，使用更中性的用户排查口径。
- 关闭 Issue #3、合并 Dependabot PR #2 后更新项目状态。
- 说明翻译表集中更新节奏、繁体中文计划和生成资源包边界。
- 统一 README、Release 和 Issue 回复中的漏翻收集、补丁体积和发布下载说明。
- 普通生成脚本在当前游戏版本缺少部分旧 `term` 时会提示并继续生成，不再直接中断。
- 记录新版新增文本可能暂时保持原文，等待后续集中整理翻译表。

### Fixed

- 补齐 Issue 模板和 Dependabot 使用的 `needs-triage`、`dependencies` 标签。
- 将开发测试依赖更新到 `pytest==9.1.1`。
- 修复一键生成脚本中 Python 构建输出污染函数返回值、导致路径识别出错的问题。
