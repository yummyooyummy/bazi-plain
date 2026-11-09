# 安装说明

[返回 README](../README.md)

## 需要什么

- Git，或者能下载解压 ZIP 也行。
- Python 3.9 或更新版本。依赖锁定在 [requirements.txt](../requirements.txt) 里：lunar-python 1.4.9、astronomy-engine 2.1.19、tzdata 2026.6。三个都是纯 Python 包，不需要编译。
- 下载依赖时要联网。程序运行时不联网。
- 不需要任何 API 密钥。

实际验证过的 Python 版本，见 [CHANGELOG](../CHANGELOG.md) 里本版的说明。

## 第一步：把文件放到技能目录

技能目录的名字必须是 `bazi-plain`，要和 [SKILL.md](../SKILL.md) 开头的 `name` 一致。

**Claude Code**（个人技能，所有项目都能用）：

```sh
git clone https://github.com/yummyooyummy/bazi-plain.git ~/.claude/skills/bazi-plain
```

只想在某一个项目里用，就放到那个项目的 `.claude/skills/bazi-plain/`。

**Codex**（个人技能）：

```sh
git clone https://github.com/yummyooyummy/bazi-plain.git ~/.agents/skills/bazi-plain
```

只想在某一个仓库里用，就放到该仓库的 `.agents/skills/bazi-plain/`。

**两个都想用：** 最简单的办法是各放一份。

Codex 的官方文档写明支持符号链接的技能文件夹，所以也可以只放一份在 `~/.claude/skills/bazi-plain`，再给 Codex 建一个链接：

```sh
mkdir -p ~/.agents/skills
ln -s ~/.claude/skills/bazi-plain ~/.agents/skills/bazi-plain
```

**不用 Git：** 在 GitHub 页面点 **Code → Download ZIP**，解压后把文件夹改名为 `bazi-plain`，放到上面的位置。

## 第二步：安装依赖

在技能目录里建一个虚拟环境。SKILL.md 里的命令默认用这个位置的 Python。

macOS / Linux：

```sh
cd ~/.claude/skills/bazi-plain        # Codex 用户换成 ~/.agents/skills/bazi-plain
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows（PowerShell）：

```powershell
cd $HOME\.claude\skills\bazi-plain
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

Windows 上的路径和 macOS 不一样，SKILL.md 里写的是 `.venv/bin/python`，模型需要换成 `.venv\Scripts\python`。本版没有在 Windows 上实测过，遇到问题请开 issue。

## 第三步：确认能跑

```sh
.venv/bin/python scripts/paipan.py --chart 戊辰 戊午 戊申 己未
```

能输出一段 JSON，开头是 `"schema_version": "0.1"`、`"status": "facts_only"`，就说明装好了。这是古籍四柱模式，只查表，不需要生日。

再试一个合成的出生输入。这个日期是为测试构造的，不指向特定人物：

```sh
echo '{"date":"2000-01-01","time":"12:00","sex":"male","longitude":120,"timezone":"Asia/Shanghai","as_of":"2026-11-09"}' \
  | .venv/bin/python scripts/paipan.py
```

## 想跑测试（可选）

测试用到 pytest 和 PyYAML，所以多装一份开发依赖：

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest scripts/tests evals/tests -q -rs
```

有几项会显示 **skipped**，这是正常的。维护者在仓库外保存了少量真实人物的验收用例，公开仓库里没有这些文件，所以相关测试会跳过，不能算作“已通过”。

`tools/check_release.py` 用来检查文档链接、技能名称，以及文档里有没有残留本机路径：

```sh
.venv/bin/python tools/check_release.py
```

## 更新

```sh
cd ~/.claude/skills/bazi-plain
git pull
.venv/bin/python -m pip install -r requirements.txt
```

依赖版本有变化时，请重跑一次测试。

## 卸载

删掉技能文件夹就行，虚拟环境也在里面，一起删掉。程序没有往别的地方写文件。

## 常见安装问题

- **`python3: command not found`**：先装 Python，macOS 可以用 python.org 的安装包或 Homebrew。
- **工具里看不到技能**：先确认目录名是 `bazi-plain`、里面直接就是 SKILL.md，不要多套一层文件夹。Codex 一般会自动发现新技能，没出现就重启 Codex。
- **在聊天里让模型帮你装**：可以，但它要能执行命令，而且会征求你同意。这里不保证每个工具都会自动完成安装。
