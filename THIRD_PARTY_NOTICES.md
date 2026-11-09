# Third-party notices / 第三方权利说明

## 本项目原创内容

原创代码、提示流程和独立方法归纳采用根目录MIT。此许可不覆盖第三方数据、公版原作的署名、现代课程或网站现代编辑文字。开发缓存、私人测试和虚拟环境不属于分发文件。

## lunar-python 1.4.9

来源：https://github.com/6tail/lunar-python 。运行时依赖；scripts/data/tables.json的藏干、十神与长生基础表提取自其常量并以本项目字段包装，build_data.py记录提取过程。下列许可须随相应代码/常量的复制件保留：

```text
MIT License

Copyright (c) 2020 6tail

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Astronomy Engine 2.1.19

来源：https://github.com/cosinekitty/astronomy 。运行时依赖，用于均时差和近界交节复核；未复制第三方计算实现到本仓库。

```text
MIT License

Copyright (c) 2019-2025 Don Cross <cosinekitty@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```

## tzdata 2026.6 / IANA

Python包：https://pypi.org/project/tzdata/ ，包装许可Apache-2.0；IANA时区数据本身为public domain，说明：https://data.iana.org/time-zones/tz-link.html 。通过依赖安装，不把它的许可替换成MIT。

## GeoNames

scripts/data/cities.json的地理信息来自GeoNames，CC BY 4.0：
https://download.geonames.org/export/dump/readme.txt
https://creativecommons.org/licenses/by/4.0/

采用cities15000.zip与CN.zip，取选定城市及中国ADM1/ADM2条目、中文别名，重命名字段，不修改坐标。每条保留geonameid和来源页面。数据文件记录抓取日期、原下载文件SHA-256及变更说明；数据不改授MIT。数据可能含历史别名、旧行政区和代表点，不保证医院精度或官方行政清单现势性。

## 行政名称覆盖基准

scripts/tests/prefecture_names.json的事实名称基准来自modood/Administrative-divisions-of-China的dist/cities.json，原项目WTFPL：
https://github.com/modood/Administrative-divisions-of-China/blob/master/LICENSE

只选地级名称及直辖市名称作回归检查，保留来源和修改时间；没有用其数据代替GeoNames坐标。

## 公版古籍、维基文库与现代材料

《子平真诠》《滴天髓阐微》《穷通宝鉴》的公版原作只作必要短引及方法出处；标题、作者、篇名、链接、可用时的页面修订记录写在references中。引用不等同于认可旧式断语。编辑性现代文字不因附在古籍页上就自动成为公版。维基条款见：https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content 。若未来采纳受CC BY-SA保护的编辑改编，须按实际页面许可单独处理。

梁湘润《子平概论》、王德峰《中国古代命理学》的课程及教材不以任何形式重新许可；本仓库只收入独立表达的方法归纳与参考链接，不包含逐字稿、字幕或教材原文。

## 竞品

仅作源代码调研，没有复制xuemian168（Apache-2.0）或jinchenma94（MIT）的实现；固定提交见RESEARCH.md。若将来复制其代码，须另保留相应许可与版权，不以本文件概括性说明替代。

## 开发依赖

pytest（MIT）、PyYAML（MIT）等通过requirements-dev.txt安装，不随项目源码打包分发；各依赖的许可证在其安装包和上游仓库中保留。
