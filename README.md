# Wiki Bot

[![GitHub license](https://img.shields.io/github/license/re0wiki/wiki-bot)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/re0wiki/wiki-bot)](https://github.com/re0wiki/wiki-bot/commits)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![CodeFactor](https://www.codefactor.io/repository/github/re0wiki/wiki-bot/badge)](https://www.codefactor.io/repository/github/re0wiki/wiki-bot)
[![Discord server](https://img.shields.io/discord/779185920670171136?label=discord&logo=discord&logoColor=white)](https://discord.gg/F554jbmEUd)
[![Telegram group](https://img.shields.io/badge/Telegram-re0wiki-26A5E4.svg?logo=telegram)](https://t.me/re0wiki)

用于 [Re:从零开始的异世界生活 Wiki | Fandom](https://rezero.fandom.com/zh) 的一些脚本。

## Deployment

- **本项目**：`git clone --recurse-submodules https://github.com/re0wiki/wiki-bot.git`
- **Python**：[conda-forge/miniforge](https://github.com/conda-forge/miniforge#install)
- **requirements**：`conda env create -f environment.yml`
- [机器人密码 | Re:从零开始的异世界生活 Wiki | Fandom](https://rezero.fandom.com/zh/wiki/Special:BotPasswords)
- **用户配置文件**
  1. [user-config.py#L17](./user-config.py#L17)
  2. 同目录下创建`user-password.py`并填写，格式为`('<UserName>', BotPassword('<BotName>', '<BotPassword>'))`

## Usage

- [pywikibot/scripts at master · wikimedia/pywikibot](https://github.com/wikimedia/pywikibot/tree/master/scripts#readme)
- `bash auto.sh`
- `python main.py -h`
- `python rename.py -h`
