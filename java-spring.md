# Java/Spring Boot 编码规范

> 版本: 4.1 | 更新: 2026-01-21

---

## 命名约定

### 类命名

| 类型 | 规则 | 示例 |
|-----|------|-----|
| 实体类 | 驼峰命名 | `PromotionPlan` |
| Controller | `*Controller` | `ProductController` |
| Service 接口 | `I*Service` | `IProductService` |
| Service 实现 | `*ServiceImpl` | `ProductServiceImpl` |
| Mapper | `*Mapper` | `ProductMapper` |
| DTO | `*DTO` | `ProductDTO` |
| 请求对象 | `*Req` | `ProductPageReq` |
| 响应对象 | `*Rsp` | `ProductDetailRsp` |
| 枚举类 | `*Enum` | `OrderStatusEnum` |

### 变量命名

| 类型 | 规则 | 示例 |
|-----|------|-----|
| 方法/字段 | `lowerCamelCase` | `getUserById` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_BATCH_SIZE = 1000` |
| 数据库表 | `lower_snake_case` | `promotion_plan` |
| 接口路径 | `kebab-case` | `/product-catalog/page` |

---

## Import 规则

- ❌ 禁止使用全限定类名，必须先 import 后使用简单类名
- ✅ 静态成员使用 `import static`

```java
import static com.dsl.selection.component.constant.Constant.MAX_BATCH_SIZE;
import static com.dsl.base.exception.util.ServiceExceptionUtil.exception;
```

---

## 依赖注入

- ✅ 新代码使用 `@RequiredArgsConstructor` + `private final` 构造器注入
- ❌ 新代码禁止 `@Autowired` 字段注入
- ⚠️ 存量代码不强制要求修改

```java
// ✅ 正确（使用 Lombok）
@Service
@RequiredArgsConstructor
public class ProductService {
    private final ProductMapper productMapper;
}

// ❌ 错误
@Service
public class ProductService {
    @Autowired
    private ProductMapper productMapper;
}
```

---

## 日志规范

### 基本要求

- 使用 `@Slf4j` 注解
- 使用占位符 `{}`，❌ 禁止字符串拼接
- 业务名称用中括号标识：`[业务名称]`
- 敏感信息必须脱敏（手机号、身份证、密码、Token）

### 必须打印的节点

- 业务方法入口（打印参数）
- 数据库查询结果（特别是查询为空时）
- 调用外部系统前后（Feign、HTTP、MQ）
- 数据库写操作（插入、更新、删除）
- 异常情况（ERROR 级别，必须包含堆栈）

### 日志格式

```java
// ✅ 正确
log.info("[促销目录生成]，生成数据，计划ID: {}，分区数量: {}", planId, zoneCount);

// ❌ 错误：字符串拼接
log.info("[促销目录生成]，计划ID: " + planId);

// ❌ 错误：没有业务标识
log.info("生成数据，计划ID: {}", planId);
```

### 日志级别

- `INFO`：关键业务流程
- `WARN`：警告信息（不影响业务）
- `ERROR`：错误异常（必须包含堆栈 `log.error("xxx", e)`）
- `DEBUG`：详细调试信息

---

## 异常处理

使用 `ServiceExceptionUtil` 抛出业务异常：

```java
import static com.dsl.base.exception.util.ServiceExceptionUtil.exception;
import static com.dsl.base.exception.util.ServiceExceptionUtil.exception0;

// 方式一：自定义错误码（推荐）
if (record == null) {
    throw exception(EXPORT_RECORD_NOT_EXISTS);
}

// 方式二：全局错误码 + 自定义消息
if (config == null) {
    throw exception0(GlobalErrorCodeConstants.BAD_REQUEST.getCode(), "配置不存在");
}
```

❌ 禁止直接 `throw new RuntimeException()`

---

## Controller 层规范

### HTTP 方法约定

| 场景 | 方法 | 示例 |
|-----|------|-----|
| 单个资源查询 | GET | `GET /product/{id}` |
| 列表/条件查询 | POST | `POST /product/list` |
| 新增 | POST | `POST /product/add` |
| 修改 | POST | `POST /product/update` |
| 删除 | POST | `POST /product/delete` |

### 职责单一

Controller 只负责：接收参数、调用 Service、返回结果。

❌ 禁止在 Controller 写业务逻辑（查询数据库、条件判断、数据处理等）。

### 返回类型

统一使用 `CommonResult<T>`：

```java
public CommonResult<ProductDetailRsp> getDetail(@Valid @RequestBody ProductDetailReq req)
public CommonResult<List<StoreItemDTO>> listStoreItems(@Valid @RequestBody QueryItemReq req)
public CommonResult<IPage<ProductPageDTO>> getPage(@Valid @RequestBody ProductPageReq req)
public CommonResult<Void> submitForApproval(@Valid @RequestBody SubmitApprovalReq req)
```

---

## 参数校验

- Controller 类添加 `@Validated`
- 方法参数使用 `@Valid @RequestBody`
- Req 对象字段使用校验注解

```java
@Data
public class ProductAddReq {
    @NotBlank(message = "商品编码不能为空")
    private String itemCode;

    @NotNull(message = "商品价格不能为空")
    @DecimalMin(value = "0.01", message = "商品价格必须大于0")
    private BigDecimal price;
}
```

### 嵌套对象校验

嵌套对象需要加 `@Valid` 才能触发内部校验：

```java
@NotNull(message = "用户信息不能为空")
@Valid  // 必须加
private UserInfo userInfo;
```

---

## Service 层

### 复杂度控制

- ✅ 使用卫语句代替多层 if-else 嵌套
- 方法长度不超过 50 行
- if-else 嵌套不超过 2 层
- 超过 3 个分支考虑策略模式

```java
// ❌ 错误：多层嵌套
if (order != null) {
    if (order.getStatus() == 1) {
        if (order.getAmount() > 0) {
            // 业务逻辑
        }
    }
}

// ✅ 正确：卫语句
if (order == null) {
    throw exception(ORDER_NOT_EXISTS);
}
if (order.getStatus() != 1) {
    throw exception(INVALID_STATUS);
}
processPayment(order);
```

---

## 幂等性设计

写接口必须保证幂等，防止重复提交导致数据异常。

| 方案 | 适用场景 | 说明 |
|-----|---------|-----|
| 唯一索引 | 防止重复插入 | 数据库层面保证 |
| Token 机制 | 表单重复提交 | 提交前获取 token，使用后失效 |
| 状态机 | 状态流转操作 | 只允许特定状态转换 |
| 业务单号去重 | 支付、扣款等 | 基于 orderNo 判断是否已处理 |

---

## 并发控制

### 乐观锁（推荐）

适用于冲突较少的场景：

```java
// Entity 增加版本号
@Version
private Integer version;
```

更新时检查版本号，失败则抛出异常或重试。

### 分布式锁

使用 Redisson `RLock`：

- 设置合理的等待时间和锁超时时间
- 在 finally 中释放锁
- 只释放自己持有的锁 `lock.isHeldByCurrentThread()`

---

## 缓存规范

### Key 命名

格式：`{业务}:{模块}:{标识}`

```java
String key = "promotion:plan:" + planId;
String key = "user:info:" + userId;
```

### TTL 设置

| 数据类型 | TTL | 说明 |
|---------|-----|-----|
| 热点数据 | 1-5 分钟 | 高频访问 |
| 普通数据 | 30 分钟 | 一般业务数据 |
| 配置数据 | 1 小时 | 变更少 |
| 永不过期 | ❌ **禁止** | 必须设置 TTL |

### 缓存穿透防护

空值也缓存（短 TTL 如 5 分钟），防止缓存穿透。

### 缓存更新策略

先更新数据库，再删除缓存。

---

## 对象转换

- ❌ 禁止直接返回 Entity，必须转换为 DTO/Rsp
- 使用 `BeanUtils.copyProperties(source, target)` 或 MapStruct
- 注意：`BeanUtils.copyProperties` 是浅拷贝，嵌套对象需手动处理

---

## 配置安全

以下配置 ❌ 禁止写在代码或本地配置文件：

- 数据库密码
- Redis 密码
- 第三方 API Key / Secret
- JWT 密钥
- 加密盐值

✅ 敏感配置存储在 Nacos 配置中心，按环境隔离。

❌ 禁止在日志中打印敏感配置。

---

## Mapper 层规范

- 简单查询使用 MyBatis Plus Lambda API
- 复杂查询使用 MyBatis XML
- ✅ 使用 `#{}` 预编译参数，防止 SQL 注入
- ❌ 禁止使用 `${}` 直接拼接
- 动态排序使用 `<choose>` 白名单，不直接拼接字段名

```xml
<!-- ✅ 动态排序安全写法 -->
ORDER BY
<choose>
    <when test="orderColumn == 'create_time'">create_time</when>
    <when test="orderColumn == 'update_time'">update_time</when>
    <otherwise>id</otherwise>
</choose>
```

---

## 数据库表设计规范

### 基础字段要求

实体类继承 `BaseDO` 时，建表语句**必须包含**以下基础字段：

| 字段名 | 类型 | 说明 | 必须 |
|--------|------|------|------|
| `id` | `bigint` | 主键，自增 | ✅ |
| `create_time` | `datetime` | 创建时间 | ✅ |
| `update_time` | `datetime` | 更新时间 | ✅ |
| `creator` | `varchar(64)` | 创建者 | ✅ |
| `updater` | `varchar(64)` | 更新者 | ✅ |
| `deleted` | `bit(1)` | 逻辑删除标记 | ✅ |

### 建表语句模板

```sql
CREATE TABLE `table_name` (
    `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
    -- 业务字段...
    `creator` varchar(64) DEFAULT '' COMMENT '创建者',
    `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updater` varchar(64) DEFAULT '' COMMENT '更新者',
    `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `deleted` bit(1) NOT NULL DEFAULT b'0' COMMENT '是否删除',
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='表注释';
```

### 实体类继承

```java
// ✅ 正确：继承 BaseDO，自动拥有基础字段
@Data
@TableName("promotion_plan")
@EqualsAndHashCode(callSuper = true)
public class PromotionPlan extends BaseDO {

    @TableId(type = IdType.AUTO)
    private Long id;

    // 业务字段...
}
```

### 字段命名规范

| 规则 | 示例 |
|------|------|
| 表名、字段名使用 `snake_case` | `promotion_plan`、`create_time` |
| 布尔字段使用 `is_` 前缀或动词 | `is_active`、`deleted` |
| 时间字段使用 `_time` 后缀 | `create_time`、`effect_time` |
| 状态字段使用 `status` | `order_status`、`approval_status` |

### 索引规范

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| 主键 | `PRIMARY KEY` | `PRIMARY KEY (id)` |
| 唯一索引 | `uk_表名_字段` | `uk_order_order_no` |
| 普通索引 | `idx_表名_字段` | `idx_order_user_id` |
| 联合索引 | `idx_表名_字段1_字段2` | `idx_order_user_id_status` |

```sql
-- 索引示例
CREATE UNIQUE INDEX `uk_order_order_no` ON `order` (`order_no`);
CREATE INDEX `idx_order_user_id` ON `order` (`user_id`);
CREATE INDEX `idx_order_create_time` ON `order` (`create_time`);
```

---

## 批量处理

超过 1000 条记录必须分批处理：

```java
int batchSize = 1000;
for (int i = 0; i < list.size(); i += batchSize) {
    List<Entity> batch = list.subList(i, Math.min(i + batchSize, list.size()));
    saveBatch(batch);
}
```

---

## 事务控制

### 基本规则

- 多表操作必须加 `@Transactional(rollbackFor = Exception.class)`
- ⚠️ 事务方法必须是 `public`（private 不生效）
- ⚠️ 避免同类方法内部调用（代理失效）
- 长事务拆分，避免锁表时间过长

### 多数据源事务限制

**⚠️ 重要**：`@Transactional` 只对主数据源生效，事务方法中 ❌ 禁止混用多个数据源。

```java
// ❌ 错误：事务中混用 MySQL 和 Doris
@Transactional(rollbackFor = Exception.class)
public void syncData() {
    // Doris 查询不在事务管理范围内
    List<Data> dorisData = dorisMapper.selectList();
    // MySQL 写入在事务中
    mysqlMapper.saveBatch(dorisData);
}

// ✅ 正确：拆分方法，事务只包裹单数据源操作
public void syncData() {
    // 1. 非事务方法查询 Doris
    List<Data> dorisData = queryFromDoris();
    // 2. 事务方法写入 MySQL
    saveToMysql(dorisData);
}

@Transactional(rollbackFor = Exception.class)
public void saveToMysql(List<Data> data) {
    mysqlMapper.saveBatch(data);
}
```

### 同类调用代理失效

```java
// ❌ 同类调用事务不生效
public void methodA() {
    this.methodB();  // methodB 的 @Transactional 不生效
}

// ✅ 正确：注入自身或拆分到另一个 Service
@Autowired
private ProductService self;

public void methodA() {
    self.methodB();  // 通过代理调用，事务生效
}
```

---

## 空安全处理

```java
// 集合判空
if (CollectionUtils.isEmpty(list)) {
    return Collections.emptyList();
}

// 链式调用防空
String city = Optional.ofNullable(user)
    .map(User::getAddress)
    .map(Address::getCity)
    .orElse("");
```

---

## 接口文档（Apifox）

项目使用 Apifox IDEA 插件，通过 Javadoc 注释自动生成接口文档。

### 注释规范

```java
/**
 * 商品管理
 */
@RestController
public class ProductController {

    /**
     * 分页查询商品
     * @param req 查询条件
     * @return 商品分页列表
     */
    @PostMapping("/page")
    public CommonResult<IPage<ProductDTO>> getPage(@Valid @RequestBody ProductPageReq req) { }
}
```

### 字段注释

```java
/**
 * 商品名称（模糊匹配）
 * @mock 阿莫西林
 */
private String name;

/**
 * 状态：0-下架，1-上架
 * @mock 1
 */
private Integer status;
```

### 特殊标签

| 标签 | 用途 |
|------|------|
| `@mock` | 字段示例值 |
| `@ignore` | 忽略该字段，不生成文档 |

---

## 异步处理

- 使用 `@Async("线程池名")` 指定线程池
- ❌ 禁止使用默认 SimpleAsyncTaskExecutor
- ❌ 禁止在同类中调用 `@Async` 方法（代理失效）
- ❌ 禁止在 `@Async` 方法中使用 `@Transactional`（事务不生效）

异步方法需要返回值时使用 `CompletableFuture<T>`。

---

## 分布式事务（RocketMQ 事务消息）

项目使用 RocketMQ 事务消息实现最终一致性：

1. 发送半消息（Half Message）→ MQ 暂存，不投递
2. 执行本地事务
3. 提交/回滚 → MQ 决定投递或丢弃
4. 异常时 MQ 回查本地事务状态

### 关键点

- 使用 `@RocketMQTransactionListener(txProducerGroup = "xxx")` 实现事务监听器
- `executeLocalTransaction`：执行本地事务，返回 COMMIT/ROLLBACK/UNKNOWN
- `checkLocalTransaction`：事务回查，必须实现幂等查询
- 消费端也要做幂等（Redis 去重）

### 回查幂等

```java
@Override
public RocketMQLocalTransactionState checkLocalTransaction(Message msg) {
    String bizId = (String) msg.getHeaders().get("bizId");
    boolean exists = orderMapper.existsByBizId(bizId);
    return exists ? COMMIT : ROLLBACK;
}
```

---

## 安全规范

### XSS 防护

- 全局 XssFilter 过滤请求参数
- 富文本字段使用 Jsoup 白名单清洗

### 权限控制（可选）

项目主要通过 DmpSystemApi 查询用户区域权限实现权限控制。

`@PreAuthorize` 注解为可选方案，存量代码中有使用。

### 敏感操作审计

使用 AOP + `@AuditLog` 注解记录关键操作日志（删除、修改等）。

---

## 性能优化

### N+1 查询

❌ 禁止循环查询数据库：

```java
// ❌ 错误
for (Order order : orders) {
    User user = userMapper.selectById(order.getUserId());  // N 次查询
}

// ✅ 正确：批量查询 + 内存关联
Set<Long> userIds = orders.stream().map(Order::getUserId).collect(Collectors.toSet());
Map<Long, User> userMap = userMapper.selectBatchIds(userIds).stream()
    .collect(Collectors.toMap(User::getId, u -> u));
```

### 深度分页

❌ 深度分页禁止使用 OFFSET（性能差）：

```sql
-- ❌ 错误
SELECT * FROM product LIMIT 100000, 10;

-- ✅ 正确：游标分页
SELECT * FROM product WHERE id > #{lastId} ORDER BY id LIMIT 10;
```

### 大数据量导出

使用流式查询 `@Options(fetchSize = 1000)` + 逐条写入，避免 OOM。

---

## 设计模式

| 模式 | 适用场景 | 说明 |
|------|----------|------|
| 策略模式 | 多分支业务逻辑 | 如支付方式、导出格式 |
| 模板方法 | 流程固定、步骤可变 | 如导出流程 |
| 责任链 | 多级审批、多步校验 | 如审批流 |

---

## 测试规范

| 类型 | 命名 | 说明 | 是否必须 |
|-----|------|-----|---------|
| Mock 测试 | `*Test.java` | 隔离外部依赖，纯逻辑测试 | **必须** |
| 集成测试 | `*IT.java` | 真实环境测试，需数据库 | 视环境 |

### Mock 测试必须覆盖

- 正常流程（happy path）
- 边界条件（空值、临界值）
- 异常分支（参数错误、业务异常）
- 依赖返回异常

### 命名规范

格式：`方法名_场景`

```java
void getById_success()
void getById_notFound()
void getById_nullId()
```

---

## 代码评审 Checklist

### 必查项

| 检查点 | 说明 |
|--------|------|
| 命名规范 | 类名、方法名、变量名是否符合规范 |
| 日志规范 | 是否有业务标识，是否使用占位符 |
| 异常处理 | 是否使用统一异常，是否有兜底处理 |
| 参数校验 | Controller 是否有 @Valid，Service 是否有业务校验 |
| SQL 安全 | 是否使用 #{}，是否有 SQL 注入风险 |
| 事务边界 | 多表操作是否有事务，是否混用数据源 |
| 空指针 | 是否有 NPE 风险，集合是否判空 |
| 幂等性 | 写接口是否保证幂等 |

### 性能检查

| 检查点 | 说明 |
|--------|------|
| N+1 查询 | 是否有循环查询数据库 |
| 深度分页 | 是否使用游标分页 |
| 批量处理 | 超过 1000 条是否分批 |
