# Fallout Shelter 简体中文补丁推广文案

本页用于复制到社区、论坛和社交平台。项目仍处于测试阶段，发布时请保留测试阶段、正版游戏和版权边界说明。

项目地址：https://github.com/mordekasiser/fallout-shelter-zh-cn-patch

## 一句话介绍

这是一个 Steam PC 版《Fallout Shelter》简体中文补丁生成工具，补丁会在用户本机基于自己的正版游戏文件生成，仓库不分发官方资源包或破解内容。

## 中文短帖

我做了一个 Steam PC 版《Fallout Shelter》的简体中文补丁工具。

使用方式比较简单：下载项目后双击 `生成汉化补丁.cmd`，脚本会查找本机 Steam 版游戏目录，用你电脑上的正版游戏资源生成补丁，然后把生成的 `FalloutShelter_Data` 文件夹拖到游戏目录覆盖即可。

项目不提供官方完整 `data.unity3d`，不发布破解包，也不绕过 Steam 或 DRM。补丁文件是在用户本机生成的。

目前项目还在测试阶段，游戏更新、安装目录差异和系统环境都可能带来问题。欢迎试用和反馈 bug，反馈时请附上系统版本、游戏版本、错误信息和复现步骤。

GitHub：https://github.com/mordekasiser/fallout-shelter-zh-cn-patch

如果你也想关注后续翻译修正和兼容性更新，欢迎 star/watch。

## 中文长帖

做了一个 Steam PC 版《Fallout Shelter》的简体中文补丁生成工具，重点是尽量把使用门槛降到普通玩家可以接受：

- 双击 `生成汉化补丁.cmd`
- 自动准备 Python 环境和依赖
- 自动查找 Steam 版游戏目录
- 用本机正版游戏文件生成汉化补丁
- 打开补丁目录和游戏目录，玩家手动拖动覆盖

这个项目的边界也写得比较清楚：仓库只包含工具代码、测试、文档和翻译 CSV，不包含官方完整资源包，不分发完整 `data.unity3d`，不提供破解包，也不修改 `FalloutShelter.exe`。

翻译表使用游戏内 `term` 作为匹配键。生成时会检查 `{0}`、`[RB]`、富文本标签等格式标记，如果游戏更新导致 key 或格式不匹配，脚本会报错，避免静默生成错位补丁。

目前仍处于测试阶段，后续会继续修 bug、补翻译和适配游戏更新。如果你愿意试用，遇到问题可以提交 Issue，最好附上系统版本、游戏版本、错误信息和复现步骤。

项目地址：https://github.com/mordekasiser/fallout-shelter-zh-cn-patch

如果这个项目对你有用，或者你想关注后续更新，欢迎 star/watch。

## English Short Post

I built an open-source Simplified Chinese patch builder for the Steam PC version of Fallout Shelter.

The repository does not distribute official game assets, full `data.unity3d` files, cracked packages, or DRM bypasses. It generates the patch locally from the user's own installed game files.

The project is still in testing. Game updates, Steam install paths, and Windows environments may cause compatibility issues, so bug reports with game version, system version, error messages, and reproduction steps are welcome.

GitHub: https://github.com/mordekasiser/fallout-shelter-zh-cn-patch

Stars/watches are appreciated if you want to follow translation fixes and compatibility updates.

## 标题备选

- Steam 版 Fallout Shelter 简体中文补丁生成工具
- 我做了一个本机生成的 Fallout Shelter 汉化补丁工具
- Fallout Shelter 简体中文补丁：不分发官方资源，本机生成
- Open-source Simplified Chinese patch builder for Fallout Shelter

## 适合发布的地方

- Fallout Shelter 贴吧、Steam 社区讨论区
- B 站动态或视频简介
- GitHub 中文社区
- Reddit：r/foshelter、r/Fallout，发布前注意社区规则
- 汉化/本地化相关论坛，重点说明不分发官方资源

## 发布注意

- 不要上传生成后的完整补丁包或 `data.unity3d`。
- 不要使用官方美术、音频或其他受版权保护素材做宣传图。
- 不要承诺游戏更新后永远可用。
- 遇到脚本报错时，提醒用户先不要覆盖游戏文件。
