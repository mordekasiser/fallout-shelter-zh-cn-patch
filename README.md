# Fallout Shelter 简体中文补丁

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D4.svg)](#使用方法)

这是 Steam PC 版《Fallout Shelter》的简体中文补丁工具。

你只需要双击脚本生成补丁，然后把生成出来的 `FalloutShelter_Data` 文件夹拖到游戏目录里，选择覆盖即可。

本项目不是通用一键汉化或运行时翻译工具，而是专门针对 Steam PC 版《Fallout Shelter》生成本地资源补丁。通用工具覆盖面广、上手快，适合临时看懂内容；这个项目更关注本游戏里的字体、文本和界面显示稳定性，目标是减少漏翻、错位、译文长度和文本框不匹配等影响长期游玩的情况。

本项目不提供官方完整 `data.unity3d`，不发布破解包。补丁文件会在你的电脑上用本机正版游戏资源生成。

翻译表使用游戏内的 `term` 作为匹配键。脚本生成补丁时会读取你当前游戏文件里的英文文本，并检查译文里的 `{0}`、`[RB]`、富文本标签等格式标记。普通生成脚本会在游戏版本和翻译表不完全一致时先提示风险，然后跳过当前版本里已经不存在的旧文本继续生成；如果格式标记不匹配，脚本仍会报错，避免静默生成错位补丁。

## 当前状态

项目仍处于测试阶段，会优先处理影响生成和使用的 bug。新版新增文本和零散漏翻会先收集，等内容积累多一些后再集中整理翻译表。不同 Steam 安装目录、系统环境或游戏版本可能触发兼容性问题。

如果脚本报错，请不要强行覆盖游戏文件。欢迎提交 Issue，并附上游戏版本、系统版本、错误信息和复现步骤。

如果脚本只是提示当前游戏版本存在文本差异并继续生成，通常说明游戏更新后有旧文本被删除或改名。新版新增文本暂时会保持原文，等漏翻内容积累多一些后再集中更新翻译表。

## 适合谁

- 想在 Steam PC 版《Fallout Shelter》中使用简体中文的玩家
- 希望补丁在本机从正版游戏资源生成，而不是下载完整改包的用户
- 愿意反馈翻译问题、脚本兼容性问题或游戏更新后适配问题的测试用户

## 使用方法

### 1. 下载并解压

普通用户建议优先下载 GitHub Releases 里的最新测试版：

```text
https://github.com/mordekasiser/fallout-shelter-zh-cn-patch/releases
```

进入最新版本页面后，在 `Assets` 里下载 `Source code (zip)` 并解压。

GitHub 页面右上角绿色 `Code` 按钮里的 `Download ZIP` 下载的是当前 `master` 源码快照，也可以使用，但它不一定对应某个已经归档说明的测试版本。

下载后解压到任意位置，例如：

```text
D:\FalloutShelterCN
```

### 2. 安装 Python

如果电脑还没有 Python，请安装 Python 3.11 或更新版本：

```text
https://www.python.org/downloads/
```

安装时请勾选：

```text
Add python.exe to PATH
```

### 3. 双击生成补丁

进入解压后的项目文件夹，双击：

```text
生成汉化补丁.cmd
```

脚本会自动：

1. 准备 Python 环境。
2. 联网安装运行依赖。
3. 查找 Steam 版《Fallout Shelter》目录。
4. 用本机正版 `data.unity3d` 生成汉化补丁。
5. 打开补丁文件夹和游戏文件夹。

如果脚本没有找到游戏，它会提示你粘贴游戏目录。

在 Steam 中可以这样找到游戏目录：

```text
Fallout Shelter -> 属性 -> 已安装文件 -> 浏览
```

### 4. 手动拖动覆盖

脚本运行完成后，会打开两个文件夹：

```text
dist\FalloutShelter_汉化补丁
```

和你的游戏目录。

把补丁文件夹里的：

```text
FalloutShelter_Data
```

拖到游戏目录里。

Windows 提示是否合并、是否覆盖时，选择：

```text
是 / 替换目标中的文件
```

然后从 Steam 启动游戏。

## 恢复原版

在 Steam 中验证游戏文件即可恢复官方文件：

```text
Fallout Shelter -> 属性 -> 已安装文件 -> 验证游戏文件的完整性
```

## 常见问题

### 运行脚本前需要打开游戏吗？

不需要。运行脚本和拖动覆盖前，请先关闭游戏。

### 会影响存档吗？

不会。这个补丁只替换游戏资源包 `FalloutShelter_Data\data.unity3d`，不处理存档、Steam、成就、联网或游戏程序本体。

### 为什么需要本机生成？

完整 `data.unity3d` 会包含官方游戏资源。本项目只提供脚本和翻译表，由用户在自己的电脑上基于已安装的正版游戏文件生成本地补丁。

生成结果仅供用户在自己的本机游戏副本中使用，不属于本仓库发布内容。

### 游戏更新后怎么办？

游戏更新后通常可以重新生成并覆盖一次。普通生成脚本会提示版本差异风险，并允许跳过当前游戏里已经不存在的旧文本继续生成。

新版新增文本暂时可能保持原文，这是预期行为。等漏翻内容积累多一些后，项目会集中整理翻译表；到时候重新生成补丁即可。如果脚本因为 `{0}`、`[RB]`、富文本标签等格式标记不匹配而报错，请不要覆盖游戏文件，等待项目适配。

### 输出文件为什么很大？

官方 `data.unity3d` 一般已经压缩打包。脚本生成补丁时会重新保存这个资源包，还会把中文字体和对应的 UI 字体引用写进去，所以生成出来的文件会比原文件大很多。

看到 `data.unity3d` 达到约 2.14GB，是因为脚本重新保存 Unity 资源包，并写入中文文本、中文字体和相关 UI 字体引用。这个项目改的是游戏读取的 `data.unity3d` 资源包；不会修改 `FalloutShelter.exe`，也不会额外安装后台程序。

脚本正常结束、输出目录里有 `FalloutShelter_Data\data.unity3d`、进游戏后中文能正常显示，就说明这次生成结果可用。如果生成过程中出现 traceback，或者进游戏后有大面积方块、空白文本、错位或崩溃，再带完整控制台输出和截图反馈。

## 高级命令

如果自动查找失败，也可以手动指定游戏目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\generate_patch.ps1 -GameDir "你的 Fallout Shelter 游戏目录"
```

运行测试：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

校验翻译表：

```powershell
.\.venv\Scripts\python.exe -m tools.translation_pipeline validate --translations translations\zh_cn_full.csv
```

如果你想用严格模式检查当前游戏资源和翻译表是否完全匹配，可以直接运行底层构建命令，并且不要加 `--allow-unmatched-translations`。普通双击脚本默认会加上这个参数，以便游戏小版本更新后仍可生成补丁。

## 免责声明

本项目是非官方社区工具，与 Bethesda、Steam、Microsoft 或其他权利方无关，也未获得其赞助、认可或授权。

本项目仓库只包含工具代码、测试、项目文档和社区维护的简体中文翻译表，不包含、托管或再分发《Fallout Shelter》的官方英文原文导出、官方游戏程序、完整资源包、可运行游戏资产、原始美术、音频、字体或其他官方素材。

用户必须自行拥有并安装合法的 PC 版《Fallout Shelter》。脚本生成的补丁文件来自用户本机游戏文件，仅供用户个人本机使用。使用本项目产生的任何兼容性问题、游戏文件损坏、更新失效、翻译错误或其他风险由用户自行承担。

本项目不修改 `FalloutShelter.exe`，不绕过 Steam、DRM、联网、存档、成就或其他访问控制，不提供破解内容，也不使用运行时注入式翻译工具。

完整声明见 [DISCLAIMER.md](DISCLAIMER.md) 和 [NOTICE.md](NOTICE.md)。

## 仓库内容

```text
生成汉化补丁.cmd             普通用户入口，双击即可生成补丁
scripts/                    一键脚本
tools/                      补丁生成、资源导出、翻译校验和补译脚本
tests/                      自动化测试
translations/               汉化 CSV
docs/                       项目文档
docs/project-status.md      当前仓库状态和治理配置摘要
LICENSE                     工具代码许可证
NOTICE.md                   第三方权利和资源边界说明
DISCLAIMER.md               免责声明
CONTRIBUTING.md             贡献说明
SECURITY.md                 安全与敏感问题报告方式
CODE_OF_CONDUCT.md          社区行为准则
CHANGELOG.md                变更记录
docs/maintainer.md          维护者更新流程和分支保护说明
```

本地生成目录已被 `.gitignore` 忽略：

```text
workspace/
dist/
submission/
```

## 参与贡献

欢迎提交翻译修正、脚本改进和问题反馈。贡献内容应只包含你有权提交的代码、文档或翻译文本。

本仓库不接受包含官方游戏资源、完整生成补丁包、第三方闭源补丁、破解内容、账号凭据、API key 或本机私有配置的 Issue、Pull Request、附件或 Release。

提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。安全、凭据或版权敏感问题请按 [SECURITY.md](SECURITY.md) 私密报告。

如果这个项目帮到了你，欢迎点一个 Star、Watch 关注后续修复和更新，也欢迎把项目分享给需要 Steam PC 版《Fallout Shelter》简体中文补丁的玩家。
