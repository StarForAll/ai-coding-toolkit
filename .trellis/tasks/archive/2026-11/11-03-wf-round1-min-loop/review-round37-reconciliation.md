# 第三十七轮外部评审的复核与修正（1 项）

- 处置编号 R73；实跑见 `validation.md` §63

## 0. 结论

| # | 原判 | 复核 | 处置 |
|---|---|---|---|
| 1 | 安装记录缺 `manifest_digest` 或为空时仍继续删除资产 | **成立** | 缺失/空值/不匹配一律 `WF_ASSET_DECISION` 阻断 |

## 1. 为什么这是缺口

上一轮只写了 `if recorded and recorded != actual`——`recorded` 为空或缺失时条件直接短路，"该清单确为本机安装清单"这一前提根本没有被验证就继续删。清单摘要不是可选项：机制稿 §10.2 的安装记录字段表里它就在，正是用来核运行期清单归属的。

## 2. 处置

```
recorded = installation.get("manifest_digest")
actual   = file_digest(manifest_path)
if not isinstance(recorded, str) or not recorded:   → WF_ASSET_DECISION（缺摘要，不猜所有权）
if recorded != actual:                              → WF_ASSET_DECISION（摘要不符）
```

两种情况都在**读取目标内容与任何删除之前**，facts 分别给 `recorded` / `manifest` 路径或 `recorded` / `actual`，便于人定位。

## 3. 用例

`r72_tests.py` 增两条：安装记录**删掉** `manifest_digest`、以及把它置为**空字符串**——都必须 `WF_ASSET_DECISION` 且登记资产仍在（实测 `removed=False`）。

## 4. 期间连带修正（N-R57）

本轮全量回归暴露两个**时区脆弱**的旧用例：`r56`、`r25r30` 用 `datetime.date.today()`（本地）算核实日期，而实现按 `records.utc_now().date()`（UTC）计日。本地刚跨到 11-04 而 UTC 仍是 11-03 时，"两天前+周期1天"被判成未到期。

判定口径本身没问题（单一 UTC 时钟），问题在用例用了另一个时钟。改为调用实现的同一函数后恢复稳定——**这不是放宽判据**，而是让用例与实现同源。
