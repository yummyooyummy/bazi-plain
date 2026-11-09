> **历史记录**：本文件记录 v0.1 公开前的开发过程（2026-11-09）。文中“不建远程、不推送”“等待 API 密钥”“评测预算”等是当时的状态，不是当前指令或计划。当前用法以 [README](README.md) 和 [CHANGELOG](CHANGELOG.md) 为准。

# v0.1 调研：九个问题

核实日期：2026-11-09。事实、实测和方案选择分别说明。本文件不含真实人物的生日。没有推送、建远程仓库或发布。

## 1. 历法库的精度、许可证和真太阳时

结论：v0.1 使用 lunar-python 1.4.9；lunar-javascript 可以作同源实现对照，不能当成完全独立的正确性证明。两者许可证都是 MIT。lunar-python 的 EightChar 提供按立春、十二节计算的年、月柱，早晚子 sect 配置，以及起运 sect 配置。它的 Solar 是日历时间对象，不携带出生地、IANA 时区和经度；调用方必须处理这些，不能把 Solar 当作已经算了真太阳时。

依据：[Python 源码](https://github.com/6tail/lunar-python/tree/master/lunar_python)、[Python 许可证](https://github.com/6tail/lunar-python/blob/master/LICENSE)、[JavaScript 许可证](https://github.com/6tail/lunar-javascript/blob/master/LICENSE)、[PyPI](https://pypi.org/project/lunar-python/)。已检查安装的 1.4.9 中 EightChar、Yun、Lunar 和寿星历计算源码。

精度不能从“输出到秒”推出来。实测 1901—2099 年十二节，共 2,388 项，lunar-python 与独立 Astronomy Engine 的太阳视黄经求根结果，绝对差最大 62.355 秒、平均 12.639 秒、95 分位 31.393 秒。这个数字是两个实现的差异，不是天文台认定的绝对误差。Astronomy Engine 的四分点验证也只承诺在其测试区间内与 USNO 相差不超过两分钟，不能据此宣称所有十二节都绝对准确到秒。

选择：lunar-python 为主要历法口径；节气边界仍按原方案的 30 分钟闸门给双盘，近界时记录独立算法的差异。年、月柱比较真实 UTC 时刻；日、时柱才用真太阳时。不能把真太阳时钟面直接与北京时间节气钟面相比较。

## 2. 均时差算法要不要换

结论：换成 Astronomy Engine 2.1.19 的太阳视赤经与格林尼治视恒星时求均时差；不使用每天固定一张分钟表，也不把近似公式宣传成秒级天文真值。它是 MIT，离线计算，不下载星历、不向外发送出生信息。

在已有三份方案及本地学习工具里没有找到上一版实际运行的均时差函数，因此不能诚实地断言“旧实现的最大误差”。另对两种常见公式作了可复现抽样：1900—2100 年，每月 1、8、15、22 日 UTC 12:00，共 9,648 个时刻。相对于上述天文计算，NOAA fractional-year 公式最大差 61.907 秒、平均 18.470 秒；常见 9.87sin(2B) 公式最大差 91.056 秒、平均 28.541 秒。这是样本结果，不是整个日期区间的数学误差上界，也不是旧实现的测量结果。

依据：[NOAA 原公式](https://gml.noaa.gov/grad/solcalc/solareqns.PDF)、[USNO 对均时差的定义](https://aa.usno.navy.mil/faq/eqtime)、[Astronomy Engine Python 文档](https://github.com/cosinekitty/astronomy/blob/master/source/python/README.md)、[许可证](https://github.com/cosinekitty/astronomy/blob/master/LICENSE)。计算使用 GeoVector、Rotation_EQJ_EQD、EquatorFromVector、SiderealTime。该库把 UTC 近似为 UT1，文档注明二者可能相差 0.9 秒；城市代表点与实际产房经度的差异还会再带来误差。

北京时间且无夏令时时，原方案“钟表时间＋(经度−120°)×4分钟＋均时差”成立。通用实现先把合法当地时间转 UTC，再算 UTC＋经度×4分钟＋均时差；这自然包含海外时区和中国历史夏令时，避免固定减 120° 用遍全球。

## 3. 城市经纬度

结论：使用 GeoNames 的城市和中国行政区数据，保留 geonameid、国家、行政级别、经纬度、时区和来源。它的当前 readme 明确是 CC BY 4.0；不把数据改标为本项目的 MIT。

依据：[数据说明及许可证](https://download.geonames.org/export/dump/readme.txt)、[下载目录](https://download.geonames.org/export/dump/)、[GeoNames 介绍](https://www.geonames.org/about.html)。cities15000 并非只含 15,000 人以上聚落，也包括相应首府；但仅凭这个文件不能声称中国地级市已逐个验收。中国 CN.zip 可补行政单元，构建时需另记覆盖数量及仍未匹配的项目。

本版实采得到3,718条记录，其中中国ADM2行政条目360条。另用[公开行政清单](https://github.com/modood/Administrative-divisions-of-China/blob/master/dist/cities.json)作名称覆盖基准，剔除“市辖区”“县”等代号后333个地级名称及4个直辖市均能匹配。该清单文件最后修改时间为2020-02-27，许可为[WTFPL](https://github.com/modood/Administrative-divisions-of-China/blob/master/LICENSE)；只作事实名称覆盖测试，不冒充2026年官方行政清单验收。基准与覆盖测试一起保留。

使用限制：代表点不等于医院坐标；边界盘需用户提供更准确经度。同名城市不得自动选第一个，先返回候选。新疆用户可能采用北京时间或新疆时间，不能只凭城市决定其出生证明的钟表口径。海外和港澳台使用各自 IANA 时区的历史规则。

## 4. 中国夏令时、港澳台及海外时区

结论：用 Python zoneinfo，加锁定版本 tzdata 2026.6；运行时明确采用此包的数据库，避免不同电脑自带时区库导致结果漂移。不自己维护一张所有国家的简表。

IANA 的 PRC 规则中，1986 年开始日在 5 月 4 日，1987—1991 年为 4 月 11 日或之后的星期日；结束日为 9 月 11 日或之后的星期日，均按规则列明的当地 02:00 切换。逐年日期是：1986 05-04—09-14；1987 04-12—09-13；1988 04-17—09-11；1989 04-16—09-17；1990 04-15—09-16；1991 04-14—09-15。回拨端的“02:00”是切换前钟表口径，回拨后有重复的 01 点时段。

依据：[IANA asia 原始规则](https://data.iana.org/time-zones/tzdb/asia)、[IANA 数据库介绍](https://data.iana.org/time-zones/tz-link.html)。香港 Asia/Hong_Kong、澳门 Asia/Macau、台湾 Asia/Taipei 都有自己的历史夏令时，不能套用 PRC 起止表。海外按出生地的 IANA 区域。不存在的春季跳时输入拒绝排盘；秋季重复时刻必须让用户指定 fold 或确认偏移，不能默选。

## 5. 一个 skill 怎样兼容多平台

结论：采用 Agent Skills 的公共最小格式：目录名 bazi-skill，根部 SKILL.md，YAML frontmatter 仅依赖 name、description；正文相对路径链接 scripts/ 和 references/。不绑定某个平台的 MCP、浏览器或私有工具。需要 Python 的行为清楚声明；没有执行环境时，只解读用户确认的外部排盘，并注明未经本程序核验，不许偷偷改为模型心算。

依据：[Agent Skills 规范](https://agentskills.io/specification)、[OpenAI 官方 skills 文档](https://learn.chatgpt.com/docs/build-skills)、[Claude Code skills 文档](https://code.claude.com/docs/en/skills)、[Claude 官方介绍](https://support.claude.com/en/articles/12512176-what-are-skills)。Codex 支持 ~/.agents/skills 和项目 .agents/skills；Claude Code 使用 ~/.claude/skills 或项目 .claude/skills。同一个文件夹可以分别复制或链接过去，不需要维护两份正文。此次只搭建项目，不自动安装到这些目录。

“任何模型稳定”是评测目标，不是格式本身能担保的能力。没有工具执行能力、上下文不足或不能严格按格式输出的模型，必须显示降级，不能伪称相同能力。

## 6. 代码、古籍和讲座的版权

用户已选择：本项目原创代码与原创方法归纳采用 MIT，保留第三方的许可证和署名。

- lunar-python、lunar-javascript、Astronomy Engine：MIT，分发或复制其代码时保留各自版权和许可证。
- GeoNames 数据：CC BY 4.0，注明来源、许可证、提取/改名等改动，并保留来源 ID。
- 古籍原作的公版地位，与网站导航、现代注释、现代整理文字的权利分开判断。只放必要的公版短条文，记录作者/篇名、页面、修订或历史链接。若实际使用受 CC BY-SA 保护的编辑文字，应另外标注并满足其要求，不能靠项目 MIT 覆盖。
- 梁湘润、王德峰材料：按你的规则，只写原创的方法归纳和参考出处，不收入课程逐字稿、字幕、教材整段或大段改写。注明出处并不自动取得复制整篇材料的许可。其他人的详细命例叙述也不当作通用可复制模板。

依据：[Wikisource 版权政策](https://wikisource.org/wiki/Wikisource:Copyright_policy)、[Wikimedia 使用条款第7节](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)、[WIPO 对思想与表达的区分](https://www.wipo.int/copyright/en/)。方法归纳仍需独立表达，不能用换近义词的方式重印课程。这是实施边界，不是对任意未来材料的版权许可判断。

## 7. 怎样评测跨模型结论一致性

结论：先比较结构化分析卡，再检查报告，不用“看起来像”作主要分数，也不把模型彼此一致当作算得准或预测有效。

每次输入相同脚本证据包、同一版规则、同一张调候表；固定版本和参数，记录模型、提示词哈希、脚本版本。每模型至少跑三次。先做硬校验：四柱及大运不得改、缺信息必须停、双盘不能丢、低于60%不能提前给细运。再比较从格候选、格局、三线喜忌、倾向数值、闸门状态和出处。主要指标为硬规则违规率、字段完全一致率、候选集合一致率、同一模型重复一致率、与人工标注的符合度；把握级别不能代替这些指标。

倾向百分比另由确定性计分脚本计算，保留证据 ID、加减分和去重记录；它是约定的倾向分，不是科学统计概率。历史回答不能用来选择性忽略反例，校准集和未来检验集要分开。评测集只放已核对的古籍四柱，不放真实人物生日。

依据：[Agent Skills 验证建议](https://agentskills.io/skill-creation/best-practices)、[promptfoo 的断言说明](https://www.promptfoo.dev/docs/configuration/expected-outputs/)。后者可作可选自动化容器，v0.1 不要求外部服务或 API；没有实际跑多个模型时，明确记“尚未验证跨模型一致性”。

## 8. 两个竞品的当前实现

本次按固定提交核实，不引用容易变化的星数作质量证据。

- xuemian168/bazi-skill，提交 d4c53040c4015cf20d6c53a9efd9563a26fff60f，Apache-2.0。[ganzhi_facts.py](https://github.com/xuemian168/bazi-skill/blob/d4c53040c4015cf20d6c53a9efd9563a26fff60f/scripts/ganzhi_facts.py) 本身主要是命令行入口，实际关系计算在 ganzhi 包；它接收原局和大运等，不能把这个入口当作完整出生排盘引擎。值得参考事实层与解读层分开、输入校验、JSON 输出。复制代码要带 Apache 许可证及适用的 NOTICE；本项目暂不复制其实现。
- jinchenma94/bazi-skill，提交 112a5d84cd1a001a0038cafca3be68d93e4c0cc9，MIT。[pai_pan.py](https://github.com/jinchenma94/bazi-skill/blob/112a5d84cd1a001a0038cafca3be68d93e4c0cc9/scripts/pai_pan.py) 当前是约1,400行的标准库历法实现，包含儒略日、太阳黄经和起运。其代码说明仍是默认北京时间钟表时，不完整计算真太阳时，并在23点换日；因此不满足本项目 R2、R3 的默认口径。可参考独立日柱校验、明确锚点及测试组织，不能直接拿来替换本项目引擎。

依据：[前者仓库许可证](https://github.com/xuemian168/bazi-skill/blob/d4c53040c4015cf20d6c53a9efd9563a26fff60f/LICENSE)、[后者仓库许可证](https://github.com/jinchenma94/bazi-skill/blob/112a5d84cd1a001a0038cafca3be68d93e4c0cc9/LICENSE)。竞品的具体依赖、时区与子时口径应按本次固定提交判断，不能只凭功能介绍认定符合本项目规则。

## 9. 中国大陆合规与免责声明

结论：README 应写传统文化研究、非科学预测、娱乐参考、非医疗/法律/投资建议、不支持重大人生决策，不收集无关身份资料，不售改运用品、不保证结果。倾向值不是发生概率。还应声明默认离线、模型调用方可能把证据包发给第三方、个人材料应由本人控制。免责声明不等于自动合规。

[《网络信息内容生态治理规定》](https://www.cac.gov.cn/2019-12/20/c_1578375159509309.htm)第六条第七项涉及宣扬封建迷信；不能简单认定“开源就没有内容风险”。[《生成式人工智能服务管理暂行办法》](https://www.cac.gov.cn/2023-07/13/c_1690898327029107.htm)第二条区分向境内公众提供生成式AI服务，与未向公众提供服务的研发应用。单纯本地工具和公开运营一个服务不是同一种场景。未来若做网站、收费服务、账号体系、收集生日或对外生成报告，需要重新按实际功能、用户和部署地核查适用义务；本次不开设服务、不处理这些部署事项，也不声称现有声明足以替代届时的专业合规判断。

## 本次已确认的三项决定

1. 报告闸门以模板的规则表为准：低于60%先问，60%—79%可出并列报告；修正示例里“60%必须先问”的矛盾表述，不改R1—R10。
2. 原创部分采用MIT，第三方内容保留各自权利。
3. GC04以正确时柱和30分钟内给备选验收；“39秒”留作旧结果参考，实际秒数由固定坐标和算法记录。

## 尚不能据此承诺的事情

六个用例通过不等于所有年代、所有边界都零错误；跨模型稳定性还要实际运行多个模型评测。生日从项目目录移到外部本地测试夹，不只依赖.gitignore，也不把改名后的真实生日当成可发布数据。
