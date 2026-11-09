# 参与贡献

谢谢你愿意帮忙。下面是几条约定，先看再动手能省不少来回。

## 最需要的帮助

- **排盘错误。** 某个输入算出的干支、节气交界、真太阳时或大运和你核对的结果不一样。
- **出处问题。** 规则标错了书篇、引文和公版原文对不上，或者有更好的电子本链接。
- **说法不清楚。** 文档或报告模板里普通人看不懂的地方。
- **安装问题。** 尤其是 Windows 和不同 Python 版本。

## 第一条：不要贴真实生日

issue、PR、评论里都不要出现真实的出生日期和时间，包括你自己的。

复现排盘问题时：

- 用古籍四柱（`scripts/paipan.py --chart ...`）；
- 或者构造一个**合成时间**，能触发同样的情况就行，比如同样落在晚子时，或同样离节气交界几分钟。

化名加真实生日也不行，化名保护不了生日。

## 开发环境

```sh
git clone https://github.com/yummyooyummy/bazi-plain.git
cd bazi-plain
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest scripts/tests evals/tests -q -rs
.venv/bin/python tools/check_release.py
```

有几项测试显示 skipped 是正常的：它们读取维护者放在仓库外的私人验收用例。

## 改动的范围

| 想改的东西 | 怎么做 |
| --- | --- |
| 错别字、说明文字、安装文档 | 直接提 PR |
| 程序计算（`scripts/*.py`、`scripts/data/`） | 先开 issue 说明问题和依据。PR 里要附上能复现的合成测试，并保证原有测试全部通过 |
| 方法资料（`references/`） | 每条新增或修改都要写出处：古籍写书名和篇名，附电子本链接；独立归纳要标明“方法归纳” |
| SKILL.md 开头的 R1—R10 | 这是项目底线，请先开 issue 讨论，不要在 PR 里顺手改 |
| 报告模板的写法（文字把握、财运六项、感情五项、健康口径） | 同上，先讨论 |

## 引用和版权

- 公版古籍（《子平真诠》《滴天髓阐微》《穷通宝鉴》等）可以短引，注明篇目和所用版本。
- 现代著作、讲座、网络文章只做方法归纳并注明出处，不要贴原文、字幕或逐字稿。
- 新增第三方数据或依赖时，在 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 里补上许可证说明。

## 写作风格

- 说人话。专业词第一次出现时顺手解释一句。
- 把握写成“把握：高 / 中 / 低”，运势写“好 / 一般 / 要注意”。不用圆点评级、颜色或表情符号。
- 不写“必然”“注定”，不写旧式断语（如“克夫”），不预测疾病、寿命、事故。
- 不夸大：程序测试只证明排盘事实，不证明解释灵验。

## 提交 PR 前

- [ ] 测试通过：`python -m pytest scripts/tests evals/tests -q`
- [ ] `python tools/check_release.py` 通过
- [ ] 没有真实生日、个人输入文件、截图或本机路径
- [ ] 改了行为的，在 [CHANGELOG.md](CHANGELOG.md) 的“未发布”下面加一行

提交贡献即表示你同意按本项目的 [MIT 许可证](LICENSE)发布这些内容。
