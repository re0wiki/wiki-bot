# Wiki Bot

[![GitHub license](https://img.shields.io/github/license/re0wiki/wiki-bot)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/re0wiki/wiki-bot)](https://github.com/re0wiki/wiki-bot/commits)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![CodeFactor](https://www.codefactor.io/repository/github/re0wiki/wiki-bot/badge)](https://www.codefactor.io/repository/github/re0wiki/wiki-bot)
[![Discord server](https://img.shields.io/discord/779185920670171136?label=discord&logo=discord&logoColor=white)](https://discord.gg/F554jbmEUd)
[![Telegram group](https://img.shields.io/badge/Telegram-re0wiki-26A5E4.svg?logo=telegram)](https://t.me/re0wiki)

用于 [Re:从零开始的异世界生活 Wiki | Fandom](https://rezero.fandom.com/zh) 的一些脚本。

核心功能：把英文站页面/图片/图库同步到中文站，并用自定义规则（译名表、格式规范）批量整理中文站内容。

## Deployment

- **本项目**：`git clone --recurse-submodules https://github.com/re0wiki/wiki-bot.git`（`pywikibot/` 是 submodule，指向 re0wiki 的定制 fork，必须拉下来）
- **Python**：3.14，用 [uv](https://docs.astral.sh/uv/) 安装依赖：`uv sync`
- [机器人密码 | Re:从零开始的异世界生活 Wiki | Fandom](https://rezero.fandom.com/zh/wiki/Special:BotPasswords)
- **用户配置文件**
    1. [user-config.py#L17](./user-config.py#L17)（账号名，默认 IchiSanNi）
    2. 同目录下创建 `user-password.py` 并填写，格式为 `('<UserName>', BotPassword('<BotName>', '<BotPassword>'))`

## Usage

- 循环执行全部维护任务（常驻）：`python main.py 231`（加 `-s` 为模拟运行，不写 wiki）；单个任务：`python main.py <任务名或编号>`（`-h` 查看完整列表，任务名稳定、编号随插入平移）
- 所有 pywikibot 自带脚本也可直接用：`python pywikibot/pwb.py <script> ...`，参见 [pywikibot/scripts at master · wikimedia/pywikibot](https://github.com/wikimedia/pywikibot/tree/master/scripts#readme)

## Status

当前运行状态见 [User:IchiSanNi/jobs](https://rezero.fandom.com/zh/wiki/User:IchiSanNi/jobs)。

## For AI agents

仓库结构、fork 定制说明、译名维护工作流等见 [AGENTS.md](./AGENTS.md)。
