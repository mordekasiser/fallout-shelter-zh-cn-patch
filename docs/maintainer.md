# Maintainer Notes

本页记录维护者更新仓库时需要遵守的流程，避免误删主分支、强推覆盖历史、提交生成资源或发布乱码评论。

当前仓库状态、打开事项和治理配置摘要见 [project-status.md](project-status.md)。

## `master` 分支保护

GitHub 仓库已启用 ruleset：`Protect master`。

当前规则保护 `master` 的历史安全和外部贡献流程：

- 禁止删除 `master`。
- 禁止 non-fast-forward push，也就是禁止 force push 覆盖历史。
- 外部贡献必须通过 Pull Request。
- Pull Request 需要至少 1 个 approving review。
- Pull Request 合并前必须通过 GitHub Actions 的 `tests` status check。

仓库 owner / administrator 保留 bypass 权限，用于紧急修复、维护配置或恢复仓库状态。正常情况下仍建议走 Pull Request；只有确认本地检查通过且变更很明确时，才使用 bypass 直接推送。

不要用 `git push --force` 或 `git push --delete origin master`。ruleset 会阻止这些操作；如果真的需要修复历史，先新建备份分支并在 GitHub 设置中临时调整 ruleset。

## 日常更新流程

### 外部贡献流程

1. 贡献者从 fork 或功能分支提交 Pull Request。
2. GitHub Actions 自动运行 `CI / tests`。
3. 维护者检查 diff、确认没有官方游戏资源、生成补丁包或敏感信息。
4. 至少 1 个维护者 approving review。
5. `tests` status check 通过后再合并。

### 维护者直接更新流程

维护者可以绕过 Pull Request、review 和 status check 直接推送，但直接推送前必须完成下面步骤。

1. 拉取最新远端状态。

```powershell
git pull --ff-only origin master
```

2. 修改代码、翻译或文档。
3. 运行测试和基础检查。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

4. 检查不会提交本地生成产物、官方资源或敏感信息。

```powershell
git status --short
git diff --staged
```

确认不要提交这些内容：

- `dist/`
- `workspace/`
- `submission/`
- `*.unity3d`
- `*.assets`
- 官方游戏文件、完整补丁包、破解内容、账号凭据、API key、本机私有配置

5. 按单一目的提交。

```powershell
git commit -m "type: 简短说明"
```

常用类型：

- `feat:` 功能变化
- `fix:` bug 修复
- `docs:` 文档变化
- `test:` 测试变化
- `chore:` 工具或维护配置

6. 推送。

```powershell
git push origin master
```

如果 GitHub 连接不稳定，可以按本机代理端口临时为 Git 指定代理，例如：

```powershell
git -c http.proxy=http://127.0.0.1:7897 -c https.proxy=http://127.0.0.1:7897 push origin master
```

如果本机代理不是 `7897`，请替换为实际端口。

## 处理游戏更新

游戏小版本更新后，普通生成入口允许跳过当前游戏里已经不存在的旧 term 并继续生成补丁。维护者需要区分两类问题：

- 旧 term 在新版资源中缺失：普通生成可跳过；严格模式仍可用于发现差异。
- 新版新增文本：会暂时保持原文；零散漏翻先收集，等内容积累多一些后再集中更新 `translations/zh_cn_full.csv`。

更新生成逻辑或翻译表后，至少运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

如果本机有 Steam 版游戏，也建议用真实 `FalloutShelter_Data\data.unity3d` 生成一次补丁，并确认生成产物仍在 `.gitignore` 忽略目录中。

## 发布版本流程

发布新的 GitHub Release 前，需要先确认仓库内记录和远端发布状态一致。

同一轮大更新只维护一个 Release。发布后如果只是修正文案、维护记录、Issue 回复口径或下载说明，应把当前 Release 的 tag 更新到这一轮大更新的最终提交，不再为同一轮内容另开第二个 Release。涉及新的功能范围、兼容性范围或需要单独追踪的补丁批次时，才创建新版本号。

1. 更新 `CHANGELOG.md`，把本次要发布的内容从“待发布”移到明确版本号。
2. 在 `docs/releases/` 下归档对应版本的发布说明。
3. 更新 `docs/project-status.md` 中的当前发布状态、已知问题和打开事项。
4. 运行本地检查。

```powershell
.\.venv\Scripts\python.exe -m pytest -q
git diff --check
```

5. 提交并推送记录更新。
6. 用 UTF-8 无 BOM 的发布说明文件创建 Release，避免中文在 GitHub 正文中乱码。
7. 发布后从 GitHub API 读回 Release 正文和标签信息，确认：

- tag 指向预期提交。
- GitHub Release 页面里的 `Source code (zip)` 能包含本轮最终 README 和文档说明。
- Release 正文没有 `????`、`�`、`锟斤拷` 等乱码。
- `CHANGELOG.md`、`docs/project-status.md` 和 `docs/releases/` 中的版本号一致。

## 发布记录

### `v0.1.2-alpha` - 2026-07-07

目的：修复一键生成脚本在 `py -3.11` 不可用但系统已有 Python 3.13/3.14 时提前报 “No suitable Python runtime found” 的问题，并补充底层构建命令的非默认目录说明。

记录文件：

- `CHANGELOG.md`
- `docs/project-status.md`
- `docs/releases/v0.1.2-alpha.md`

发布后回查记录：

- GitHub Release：待创建。
- GitHub Release tag：待确认指向本轮最终提交。
- GitHub Actions：待确认发布提交的 `CI / tests` 通过。
- Issue #5 / #6：已回复，发布后可补充提示用户改用 `v0.1.2-alpha` 验证。

### `v0.1.1-alpha` - 2026-06-25

目的：把 `master` 上已经完成并通过测试的生成兼容性修复发布到 GitHub Release，避免用户继续下载 `v0.1.0-alpha` 旧包后遇到已修复的旧 term 缺失报错。

记录文件：

- `CHANGELOG.md`
- `docs/project-status.md`
- `docs/releases/v0.1.1-alpha.md`

发布后回查记录：

- GitHub Release：`v0.1.1-alpha` 已创建；正文已回读确认，中文显示正常。
- GitHub Release tag：本轮文档和 Issue 口径修正完成后，更新到最终提交，确保 `Source code (zip)` 包含最新说明。
- GitHub Actions：发布提交和本轮最终提交对应的 `CI / tests` 已通过。
- Issue #3：已提示用户改用新发布版本验证并关闭；如果新版仍失败，可重新打开或新开 Issue。

## GitHub 评论和中文编码

通过 GitHub、`gh`、PowerShell 或其他 CLI 发布中文内容时，不要直接依赖 PowerShell 管道或默认 stdin 编码。优先使用 UTF-8 无 BOM 临时文件或 GitHub API JSON 请求发送。

发布后必须从 GitHub API 读回正文，确认没有 `????`、`�`、`锟斤拷` 等编码损坏痕迹。发现乱码时立即编辑原评论，不要新增重复评论。

## Issue 和依赖更新维护

Issue 模板面向中文用户，字段名应直接使用中文，避免 GitHub 页面或浏览器把英文标签翻译成不自然的内容。修改 `.github/ISSUE_TEMPLATE/` 后，应检查模板引用的标签是否存在。

当前模板和 Dependabot 依赖这些标签：

- `bug`
- `enhancement`
- `needs-triage`
- `dependencies`

处理 Dependabot PR 时，先确认标签存在，再本地跑测试。依赖更新通过 CI 后可以合并；合并后需要确认 `master` 上 CI 仍通过。如果维护者使用 owner bypass 合并常规 Dependabot PR，需要在项目状态或维护记录中说明测试和 CI 结果。
