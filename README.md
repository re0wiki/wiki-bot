# Re:从零开始的异世界生活 Wiki

用于 [Re:从零开始的异世界生活 Wiki | Fandom](https://rezero.fandom.com/zh) 的一些脚本。

## Requirements

* **本项目**：`git clone --recursive https://github.com/CCXXXI/re0wiki.git`
* **Python**：[Miniconda — Conda documentation](https://docs.conda.io/en/latest/miniconda.html)
* **依赖**：`pip install -r pywikibot/requirements.txt`
* [机器人密码 | Re:从零开始的异世界生活 Wiki | Fandom](https://rezero.fandom.com/zh/wiki/Special:BotPasswords)
* **用户配置文件**
  1. [user-config.py#L15](./user-config.py#L15)
  2. 同目录下创建`user-password.py`并填写，格式为`('<UserName>', BotPassword('<BotName>', '<BotPassword>'))`

## Usage

* [pywikibot/scripts at master · wikimedia/pywikibot](https://github.com/wikimedia/pywikibot/tree/master/scripts#readme)
* `python main.py`：运行自动任务
* `python main.py s`：运行自动任务，但不进行任何实际更改（用于调试）
* `python main.py list`：显示自动任务内容及编号
* `python main.py 3`：运行自动任务，从第3项开始
* `python re0/rename.py`：名称修改，包括移动页面、替换文本
  * 需人工检查是否破坏了部分内容（如英文名、跨语言链接等）
  * 需人工检查并视情况修改[替换任务](re0/repl.py)

