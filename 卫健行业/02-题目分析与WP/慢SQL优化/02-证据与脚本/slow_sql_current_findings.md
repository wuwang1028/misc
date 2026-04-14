# 慢SQL优化题当前发现记录

## 题目入口与要求

- 题目入口：`http://oj-10-30-15-9-46057.adworld.xctf.org.cn/`
- 访问方式为 `ttyd` 终端。
- 终端登录账号密码：`ctf/ctf`。
- `/home/ctf/README.md` 明确说明：
  1. 需要优化给定 SQL；
  2. MySQL 用户密码为 `root/root`，不要修改 root 密码；
  3. 优化后会自动生成 `/flag`。

## 已确认环境信息

- 系统：Alpine Linux。
- 当前终端普通用户：`ctf`。
- 数据库进程：MariaDB，`mysqld_safe` + `mariadbd`。
- ttyd 进程：`/usr/sbin/ttyd -P 10 -p 18080 login`。
- Web/题目容器主机名：`44a8d7d4bc3a`。

## 数据库与表结构关键信息

- 数据库：`test`
- 目标表：`event_q`、`staff_event`
- 原始索引：
  - `event_q` 仅有主键 `PRIMARY(event_id)`
  - `staff_event` 仅有主键 `PRIMARY(event_id, staff_id)`
- 数据量：
  - `event_q`：`236815`
  - `staff_event`：`827254`
- 条件选择性：
  - `staff_event where staff_id=1 and is_read=1` 共 `962` 行
  - `event_q where event_type='2' and create_date between '2023-01-01' and '2023-08-12'` 共 `97713` 行
  - 最终连接命中 `481` 行

## 原始慢查询执行情况

原始 SQL：

```sql
select q.event_id, q.event_type, q.state, q.read_url, q.create_date, q.content, q.form_serial
from event_q q, staff_event s
where q.event_id = s.event_id
  and q.content like '%权限%'
  and q.event_type='2'
  and q.create_date >= '2023-01-01'
  and q.create_date <= '2023-08-12'
  and s.is_read = 1
  and s.staff_id = 1
order by create_date desc;
```

原始 `EXPLAIN` 结果要点：

- 优化器先扫 `event_q`。
- `event_q` 类型为 `ALL`，扫描估算约 `212355` 行。
- Extra 为 `Using where; Using filesort`。
- 原始实际耗时（使用 profiling 测得）约 `5.35198351s`。

## 已验证的优化步骤

### 第一步：补充索引

已执行：

```sql
use test;
create index idx_event_type_date_id on event_q(event_type, create_date, event_id);
create index idx_staff_read_event on staff_event(staff_id, is_read, event_id);
analyze table event_q, staff_event;
```

效果：

- `event_q` 不再全表扫描，转为使用 `idx_event_type_date_id`。
- 但优化器仍优先从 `event_q` 驱动，估算扫描约 `115852` 行。
- 此时未生成 `/flag`。

### 第二步：启用持久统计并重算优化器统计信息

已执行：

```sql
set global use_stat_tables='PREFERABLY';
use test;
analyze table event_q persistent for all;
analyze table staff_event persistent for all;
```

效果：

- `EXPLAIN` 显示优化器改为从 `staff_event` 开始。
- `staff_event` 使用 `idx_staff_read_event`。
- `q` 通过主键 `PRIMARY` 做 `eq_ref` 回表。
- 虽然 `EXPLAIN` 中 `rows` 估值仍不理想，但实际耗时显著下降。

## 最终验证结果

- 优化后再次 profiling：目标查询耗时约 `0.02429139s`。
- 系统已自动生成 `/flag`。
- 已读取 flag：

```text
xctf{28a0679f83c14b2192d2423ac9a65e89eb7730e5}
```

## 初步结论

这题的关键不只是“补建索引”，而是要让 MariaDB 优化器**真正采用以 `staff_event` 为驱动表的执行计划**。仅建立复合索引仍不足以触发判题；还需要通过持久统计信息让优化器识别 `staff_id=1 and is_read=1` 的高选择性，从而把执行时间从约 `5.35s` 压缩到约 `0.024s`，最终触发 `/flag` 自动生成。
