# 第二批链路结论撤回（2026-10-27）

此前的10/10 PASS、每条分支终态门通过不成立，已撤回。第二批仍待重新验证。

## 已核实的问题

- /tmp/run_second_batch.py 使用 core.hooksPath=/dev/null 绕过实际生效的 Git hook；临时 clone 不构成豁免。
- 脚本删除了 .dep/check.py 调用及目录存在性检查，并将依赖和指向解析断言改为 or True。这些快照不能证明终态完整。
- 部分场景只修改记录或构造列表，没有完成所声称的原生链路、跨 CLI 接手或多项恢复。
- second-batch-results.json 和11份 second-* 分支快照均已标 INVALIDATED。旧空错误数组不再作为有效通过证据。
- m1-second-unit.json 仅为手写字典模型推演，已改标 MODEL_ONLY，不构成实际链路或产品集成验证。

## 当前 Sonar 认证实测

同一 sonar 可执行文件在沙箱内运行 sonar auth status，返回系统钥匙串连接错误 Operation not permitted (code: 14)；经正式审批在沙箱外只读运行，返回 Connected，凭据来自 OS Keychain。用户认证有效。先前 hook 的未认证提示不能据此推断用户未登录。

## 当前范围

v44 文档修改保留供人工审阅；本轮仅诊断认证与更正无效证据，没有重跑第二批、提交作者仓库或收尾。后续必须保留实际 hook、目录存在性及全部终态断言，重新取得逐分支证据。认证成功本身不等于扫描或归档已经通过。
