# Maintainer Notes

本页记录维护者更新仓库时需要遵守的流程，避免误删主分支、强推覆盖历史、提交生成资源或发布乱码评论。

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

维护者可以 bypass Pull Request / review / status checks，但直接推送前必须完成下面步骤。

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
- 新版新增文本：会暂时保持原文，后续更新 `translations/zh_cn_full.csv` 时再补。

更新生成逻辑或翻译表后，至少运行：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

如果本机有 Steam 版游戏，也建议用真实 `FalloutShelter_Data\data.unity3d` 生成一次补丁，并确认生成产物仍在 `.gitignore` 忽略目录中。

## GitHub 评论和中文编码

通过 GitHub、`gh`、PowerShell 或其他 CLI 发布中文内容时，不要直接依赖 PowerShell 管道或默认 stdin 编码。优先使用 UTF-8 无 BOM 临时文件或 GitHub API JSON 请求发送。

发布后必须从 GitHub API 读回正文，确认没有 `????`、`�`、`锟斤拷` 等编码损坏痕迹。发现乱码时立即编辑原评论，不要新增重复评论。
