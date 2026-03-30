# IDD

## 核心接口

- `POST /inspections`
- `GET /inspections`
- `GET /issues/summary`
- `GET /reports/export`
- `GET /authorization/status`
- `POST /authorization/upgrade`

## 交互边界

- 门店经理只能提交和查看本门店记录
- 总部用户可查看汇总与导出
- 授权状态接口对客户管理员可见
