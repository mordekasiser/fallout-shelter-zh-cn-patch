# Contributing

欢迎提交翻译修正、脚本改进和问题反馈。

## 开发环境

1. 安装 Python 3.11 或更新版本。
2. 在仓库根目录创建并使用虚拟环境。
3. 安装开发依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

提交前建议再运行：

```powershell
git diff --check
```

## 可以提交的内容

- 工具代码、测试和文档改进。
- `translations/` 下的翻译修正。
- 能帮助复现问题的错误信息、操作步骤和系统环境说明。

## 不接受的内容

- 官方游戏程序、资源包、完整 `data.unity3d`、原始美术、音频、字体或其他受版权保护的官方素材。
- 本机生成出的完整补丁包或压缩包。
- 第三方闭源补丁、破解文件、绕过 DRM 或访问控制的内容。
- API key、账号凭据、令牌、个人配置、本机绝对路径或其他敏感信息。

## Pull Request 要求

- 一次 Pull Request 只处理一个清晰目标。
- 行为变更需要补测试，至少说明已运行的测试命令。
- 影响普通用户使用方式时，请同步更新 `README.md`。
- 涉及安全、版权或凭据的问题，请优先使用 `SECURITY.md` 里的私密报告路径。
- 提交 Issue 或 Pull Request 前，请确认内容不包含上述不接受的文件或信息。

## 行为准则

参与本项目需遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
