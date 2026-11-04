# {{WF_REQUIRED:title}}

## 目标

{{WF_REQUIRED:goal}}

## 范围与触碰面

{{WF_REQUIRED:scope}}

## 方案说明

{{WF_REQUIRED:approach}}

## 不做项

{{WF_REQUIRED:non-goals}}

## 机读块

<!-- 唯一 wf-plan 块；批准/开工按此块核验。touch_paths 为仓库相对 glob。 -->

<!-- wf-plan:v1 -->
```json
{
  "schema_version": 1,
  "touch_paths": [],
  "acceptance": [
    {"id": "a1", "statement": "__WF_REQUIRED__", "verification_ids": ["v1"]}
  ],
  "verifications": [
    {
      "id": "v1",
      "invocation": {"kind": "argv", "argv": ["__WF_REQUIRED__"]},
      "cwd": ".",
      "input_refs": [],
      "required": true,
      "consume_at": "check"
    }
  ]
}
```

## 待决问题

<!-- 需要人裁决的问题按 `plan-q-<n>：` 起始行编号，同行或紧邻行给推荐答案；批准时一轮内批量作答。 -->
