# Project Status

Last updated: 2026-06-25

本页记录仓库当前维护状态，方便后续维护者、贡献者或自动化代理快速了解项目边界和治理配置。

## 当前定位

本项目是 Steam PC 版《Fallout Shelter》的本地简体中文补丁生成工具。

仓库只包含工具代码、测试、文档和社区维护的简体中文翻译表。仓库不包含官方英文原文导出、官方完整资源包、可运行游戏资产、完整 `data.unity3d`、生成后的完整补丁包、破解内容或绕过 DRM 的内容。

## 最新生成兼容性

截至本记录日期，已用当前 Steam 版游戏资源验证过一次真实生成流程，可以正常生成补丁。

生成时当前已知会提示并跳过以下旧 term：

- `Theme_Name_NewVegasExterior`
- `Theme_Name_NewVegasNightExterior`
- `Theme_Name_UltraciteExterior`

这些 term 在当前游戏资源中不存在，普通生成入口会提示风险并继续生成。v2.4.1 新增文本目前可能仍保持原文，后续更新翻译表时再补。

## 当前发布状态

最新测试发布版本：`v0.1.1-alpha`。

本次发布用于把 `master` 上已经完成的生成兼容性修复同步到 GitHub Release。旧的 `v0.1.0-alpha` 发布包仍指向 2026-05-25 的早期提交，不包含游戏资源 term 差异时继续生成的修复。用户如果遇到旧版本报错，应优先改用 `v0.1.1-alpha` 或最新 `master`。

发布说明归档在 [releases/v0.1.1-alpha.md](releases/v0.1.1-alpha.md)。

## GitHub 仓库治理

仓库已补充以下公开协作文件：

- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `CODEOWNERS`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/`
- `.github/dependabot.yml`
- `CHANGELOG.md`

Private vulnerability reporting 已启用。安全、凭据或版权敏感问题应优先通过 `SECURITY.md` 中的私密报告路径处理，不应公开贴在 Issue 中。

## 分支保护和合并规则

`master` 分支已启用 GitHub ruleset：`Protect master`。

当前规则：

- 禁止删除 `master`。
- 禁止 non-fast-forward push，也就是禁止 force push 覆盖历史。
- 外部贡献必须通过 Pull Request。
- Pull Request 至少需要 1 个 approving review。
- Pull Request 需要 CODEOWNER review。
- Pull Request 需要解决 review threads 后才能合并。
- Pull Request 合并前必须通过 GitHub Actions status check：`tests`。

仓库 owner / administrator 保留 bypass 权限，用于紧急修复、维护配置或恢复仓库状态。正常维护仍建议走 Pull Request；直接推送前必须本地跑测试、检查 diff、确认不会提交官方资源、生成产物或敏感信息。

## CI

GitHub Actions workflow：

- 文件：`.github/workflows/ci.yml`
- Workflow 名称：`CI`
- Job / required status check：`tests`
- Runner：`windows-latest`
- Python：`3.11`
- 命令：`python -m pytest -q`

最近一次已知状态：`CI / tests` 成功。

## 当前打开事项

当前已知打开事项：

- Issue #1：`[Feature]: 5月28日 v2.4.1 版本更新`
  - 已回复：普通生成入口已支持跳过当前版本缺失的旧 term 并继续生成。
  - 后续：新增文本翻译表待后续补充。
- Issue #3：`[Bug]: 错误，无法生成汉化补丁`
  - 初步判断：用户截图显示使用的是 `v0.1.0-alpha` 旧包，报错正是后续 `master` 已修复的旧 term 缺失问题。
  - 后续：引导用户改用 `v0.1.1-alpha` 或最新 `master`，如果仍失败再补完整控制台输出。
- Pull Request #2：`chore: bump pytest from 9.0.2 to 9.1.1`
  - 来源：Dependabot。
  - 后续：需要跑 CI 并确认兼容后再合并。

## 维护注意事项

- 不要提交 `dist/`、`workspace/`、`submission/` 或任何 `*.unity3d` / `*.assets` 生成资源。
- 不要提交官方游戏资源、完整补丁包、破解内容、账号凭据、API key、本机私有配置或绝对路径。
- 通过 GitHub、`gh`、PowerShell 或其他 CLI 发布中文内容时，优先用 UTF-8 无 BOM 文件或 API JSON 请求；发布后必须从 GitHub API 读回确认没有乱码。
- 对游戏版本适配变更，至少运行 `.\.venv\Scripts\python.exe -m pytest -q`。如果本机有 Steam 游戏资源，建议再做一次真实生成验证。

更多维护步骤见 [maintainer.md](maintainer.md)。
