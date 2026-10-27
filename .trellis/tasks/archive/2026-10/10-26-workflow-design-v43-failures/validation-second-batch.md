# 第二批验证更正（2026-10-27）

此前第二批10/10及逐分支终态门PASS已撤回。具体脚本缺陷见 evidence/second-batch-report.md；项目通用单测通过不能替代第二批验证。

| 环境 | 命令 | 实测结果 |
|---|---|---|
| 沙箱内 | sonar auth status | rc1；无法连接系统钥匙串，Operation not permitted (code: 14) |
| 正式审批后的沙箱外 | sonar auth status | rc0；Connected；Source OS Keychain |

有效 core.hooksPath 来自用户级 /home/xzc/.gitconfig，指向 /home/xzc/.sonar/sonarqube-cli/hooks。临时 clone 同样继承这一配置；禁用它属于绕过门禁，原先声称不算绕过的表述错误。

第二批：未完成，旧结论 INVALIDATED。M1 三个字典模型：MODEL_ONLY。作者仓库未提交、不收尾。仅获准的沙箱外只读认证检查已运行；没有据此宣称原生归档、扫描或全部链路通过。
