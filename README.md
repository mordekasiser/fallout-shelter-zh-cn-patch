# Fallout Shelter 简体中文补丁

这是 Steam PC 版《Fallout Shelter》的简体中文补丁工具。

你只需要双击脚本生成补丁，然后把生成出来的 `FalloutShelter_Data` 文件夹拖到游戏目录里，选择覆盖即可。

本项目不提供官方完整 `data.unity3d`，不发布破解包。补丁文件会在你的电脑上用本机正版游戏资源生成。

翻译表使用游戏内的 `term` 作为匹配键。脚本生成补丁时会读取你当前游戏文件里的英文文本，并检查译文里的 `{0}`、`[RB]`、富文本标签等格式标记；如果游戏更新导致 key 或格式不匹配，脚本会报错，不会静默生成错位补丁。

## 使用方法

### 1. 下载并解压

点击 GitHub 页面右上角绿色 `Code` 按钮，选择 `Download ZIP`。

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

### 为什么不直接提供覆盖包？

直接发布完整 `data.unity3d` 会包含官方资源。本项目只发布脚本和翻译表，让用户用自己电脑里的正版文件生成补丁。

你本机生成出来的 `dist\FalloutShelter_汉化补丁\FalloutShelter_Data\data.unity3d` 也不要上传网盘、群聊、论坛或 GitHub Release 二次分发。

### 游戏更新后怎么办？

游戏更新后可能需要重新生成并覆盖一次。如果脚本报错，通常说明当前翻译表和新版游戏文本不匹配，请等待项目适配新版本。

### 输出文件为什么很大？

补丁会嵌入中文字体，生成的资源包会明显变大。这是为了降低中文显示方块或空白的风险。

## 高级命令

如果自动查找失败，也可以手动指定游戏目录：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\generate_patch.ps1 -GameDir "你的 Fallout Shelter 游戏目录"
```

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

校验翻译表：

```powershell
.\.venv\Scripts\python.exe -m tools.translation_pipeline validate --translations translations\zh_cn_full.csv
```

## 项目边界

- 不提供、不托管、不再分发官方完整 `data.unity3d`。
- 不上传、不托管、不二次分发本机生成后的完整 `data.unity3d`。
- 不修改 `FalloutShelter.exe`。
- 不修改 Steam、DRM、联网、存档、成就或玩法逻辑。
- 不使用 ReiPatcher、XUnity AutoTranslator 等运行时注入方式。
- 不处理破解内容。

## 仓库内容

```text
生成汉化补丁.cmd             普通用户入口，双击即可生成补丁
scripts/                    一键脚本
tools/                      补丁生成、资源导出、翻译校验和补译脚本
tests/                      自动化测试
translations/               汉化 CSV
LICENSE                     工具代码许可证
NOTICE.md                   第三方权利和资源边界说明
```

本地生成目录已被 `.gitignore` 忽略：

```text
workspace/
dist/
submission/
```

请不要把官方资源包、生成后的完整 `data.unity3d`、压缩交付包、API key 或本机配置提交到仓库，也不要把这些文件作为 Release 附件上传。
