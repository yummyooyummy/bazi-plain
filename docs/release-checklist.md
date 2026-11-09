# 发布前检查清单（维护者用）

[返回 README](../README.md)

每次打 tag 或对外发布前逐项过一遍。命令都在仓库根目录运行。

## 程序与测试

- [ ] `python -m pip install -r requirements-dev.txt` 在干净虚拟环境里能装上。
- [ ] `python -m pytest scripts/tests evals/tests -q -rs` 没有失败。记下 passed / skipped 的数字，skipped 应只来自“仓库外私人用例不存在”。
- [ ] 维护者本机：设置 `BAZI_PRIVATE_CASES`、`BAZI_PRIVATE_LATE_ZI_CASES` 指向仓库外的私人用例，再跑一遍，确认没有 skipped。这一步的结果只写“维护者本机私人验收通过”，不写成公开 CI 的结果。
- [ ] `python scripts/paipan.py --chart 戊辰 戊午 戊申 己未` 能正常输出。

## 文档与技能入口

- [ ] `python tools/check_release.py` 通过，包括相对链接、SKILL 名称和本机路径检查。
- [ ] SKILL.md 的 R1—R10 与上一版逐行一致；若有改动，CHANGELOG 里单独说明并写明理由。
- [ ] README 引用的 `.github/assets/` 图片都在。
- [ ] CHANGELOG 的版本号和日期与 tag 一致。

## 隐私

- [ ] 准备一份**仓库外**的私人关键字清单，每行一个，比如私人用例里的生日字符串。运行：

  ```sh
  BAZI_PRIVATE_STRINGS_FILE=~/somewhere-private/strings.txt python tools/check_release.py
  ```

  这份清单本身永远不要提交。
- [ ] `git log -p` 里也搜一遍同样的关键字，历史提交同样会被公开。
- [ ] 没有新增 `--audit` 输出、个人输入 JSON、截图或测试私人目录。

## 发布

- [ ] 打 tag，例如 `v0.1.0`，在 GitHub Releases 写简短说明，可直接摘 CHANGELOG。
- [ ] 发布后看一次 Actions 的运行结果，确认 README 上的测试状态是真实的。
