# 慢SQL优化题 WP

## 一、题目信息与结论

本题为一类**数据库性能优化与环境运维**结合的赛题。题目给出一条固定 SQL，要求在不改写查询语句的前提下，通过对数据库环境进行合理优化，使其查询速度显著下降并触发自动判题。题目环境通过 `ttyd` 暴露终端，提示中明确给出了终端账户 `ctf/ctf` 与数据库账户 `root/root`，并说明优化完成后会自动生成 `/flag`。

本题最终已经成功打通，获取到的 flag 为：

```text
xctf{28a0679f83c14b2192d2423ac9a65e89eb7730e5}
```

从实战过程来看，这道题的核心并不只是“补一两个索引”，而是要让 **MariaDB 优化器真正选择正确的驱动表**。在仅补充复合索引的情况下，SQL 的执行计划虽然有所改善，但仍未通过判题；只有继续启用**持久统计信息**并重算表统计，使优化器识别出 `staff_event` 上过滤条件的高选择性，最终查询耗时才从约 **5.35 秒** 下降到约 **0.024 秒**，并成功生成 `/flag`。

## 二、环境与题目要求

在登录题目环境后，可以从 `/home/ctf/README.md` 获得直接提示。结合实际终端探测，关键环境信息如下表所示。

| 项目 | 内容 |
| --- | --- |
| 题目名称 | 慢SQL优化 |
| 题目入口 | `http://oj-10-30-15-9-46057.adworld.xctf.org.cn/` |
| 访问方式 | `ttyd` Web 终端 |
| 终端账号 | `ctf` |
| 终端密码 | `ctf` |
| 数据库账号 | `root` |
| 数据库密码 | `root` |
| 判题方式 | 优化完成后自动生成 `/flag` |
| 系统类型 | Alpine Linux |
| 数据库 | MariaDB |

本题给出的目标 SQL 如下：

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

这条 SQL 同时包含了**等值连接、范围过滤、模糊匹配和排序**。其中 `q.content like '%权限%'` 存在前导通配符，意味着常规 B-Tree 索引无法直接对该条件进行高效过滤，因此执行计划的关键，就落在了**谁先做驱动表**以及**如何尽可能缩小进入 `LIKE` 判定的数据规模**上。

## 三、初始信息收集

进入终端后，首先确认了数据库与表结构情况。数据库为 `test`，核心表为 `event_q` 与 `staff_event`。原始索引情况比较薄弱：`event_q` 只有主键 `PRIMARY(event_id)`，而 `staff_event` 只有联合主键 `PRIMARY(event_id, staff_id)`。这种设计虽然保证了主键唯一性，但并没有针对题目中的过滤条件 `staff_id=1 and is_read=1` 与 `event_type + create_date` 做专门优化。

进一步统计数据量后，可以看到两张表的规模如下。

| 表名 | 记录数 |
| --- | ---: |
| `event_q` | 236815 |
| `staff_event` | 827254 |

仅看总表规模还不足以判断优化方向，因此继续统计题目过滤条件对应的选择性。结果如下。

| 统计项 | 数值 |
| --- | ---: |
| `staff_event where staff_id=1 and is_read=1` | 962 |
| `event_q where event_type='2' and create_date between '2023-01-01' and '2023-08-12'` | 97713 |
| 最终连接命中记录数 | 481 |

这一组数据极其关键。它说明：如果能够让执行计划以 `staff_event` 为驱动表，那么在第一阶段只需要处理 **962 行**；但如果从 `event_q` 出发，即使已经利用 `event_type` 和 `create_date` 缩小范围，也仍然要处理接近 **9.8 万行**，再叠加 `LIKE '%权限%'` 和排序，整体成本就会很高。

## 四、原始执行计划分析

使用 `EXPLAIN` 对原始 SQL 进行分析后，发现优化器最初选择的是**从 `event_q` 全表或大范围扫描开始**，并在 `Extra` 中出现 `Using where; Using filesort`。这说明原始环境下存在两个明显问题。

第一，`event_q` 缺少针对 `event_type + create_date` 的组合索引，导致优化器只能从更粗糙的访问路径读取大量记录。第二，`staff_event` 现有主键顺序为 `(event_id, staff_id)`，不适合本题按 `staff_id` 和 `is_read` 先过滤，因此即便 `staff_event` 的实际过滤结果只有 962 行，优化器也难以轻易选择它作为驱动表。

在原始状态下，通过 `profiling` 实测，目标查询的耗时约为：

```text
5.35198351s
```

这也是本题之所以被定义为“慢 SQL”的直接表现。

## 五、第一阶段优化：补充复合索引

基于题目 SQL 的过滤条件，第一阶段先补充两个与查询结构强相关的索引：一个用于 `event_q` 的条件过滤，另一个用于 `staff_event` 的高选择性筛选。

```sql
use test;
create index idx_event_type_date_id on event_q(event_type, create_date, event_id);
create index idx_staff_read_event on staff_event(staff_id, is_read, event_id);
analyze table event_q, staff_event;
```

这一步的设计思路如下表所示。

| 索引名 | 建立在 | 列顺序 | 目的 |
| --- | --- | --- | --- |
| `idx_event_type_date_id` | `event_q` | `(event_type, create_date, event_id)` | 利用等值 + 范围过滤先缩小 `event_q` 的候选记录 |
| `idx_staff_read_event` | `staff_event` | `(staff_id, is_read, event_id)` | 使 `staff_id=1 and is_read=1` 可以直接命中高选择性前缀 |

执行后再次查看计划，可以看到 `event_q` 已不再是纯粹的全表扫描，而是开始使用 `idx_event_type_date_id`。这意味着优化已经取得阶段性效果。然而，这一步**仍未通过判题**，原因在于优化器虽然拿到了更好的索引，却依旧倾向于从 `event_q` 驱动，再去连接 `staff_event`。在这种情况下，进入后续 `LIKE '%权限%'` 过滤与排序的数据量仍然偏大，因此整体耗时还不够低。

换句话说，**索引是必要条件，但不是充分条件**。本题真正的瓶颈不止是缺少索引，而是优化器对数据分布的判断不够理想，没有主动选择更优的连接顺序。

## 六、第二阶段优化：启用持久统计信息

在第一阶段失败后，继续分析可知：本题 SQL 中真正高选择性的过滤条件落在 `staff_event` 上，而 MariaDB 在默认统计信息下并没有稳定地把这一点体现在执行计划里。于是第二阶段采用了**持久统计信息**的方案，让优化器重新学习表数据分布。

执行命令如下：

```sql
set global use_stat_tables='PREFERABLY';
use test;
analyze table event_q persistent for all;
analyze table staff_event persistent for all;
```

其原理在于：MariaDB 支持将统计信息持久化存储，使优化器在后续生成执行计划时，不必只依赖临时或较粗糙的抽样结果。对于本题这种“总表大，但局部条件极具选择性”的场景，持久统计信息能够更准确地告诉优化器，`staff_id=1 and is_read=1` 对 `staff_event` 的过滤非常强，从而更倾向于把 `staff_event` 作为驱动表。

重新 `EXPLAIN` 后，执行计划发生了关键变化：

| 表 | 访问类型 | 使用索引 | 说明 |
| --- | --- | --- | --- |
| `s` | `ref` | `idx_staff_read_event` | 先用 `staff_id`、`is_read` 快速筛出小结果集 |
| `q` | `eq_ref` | `PRIMARY` | 再根据 `event_id` 主键逐条精确回表 |

虽然 `EXPLAIN` 中某些 `rows` 估值仍然并不完美，但**实际执行耗时已经大幅下降**，说明优化器在真实运行路径上确实采用了更优策略。

## 七、最终验证与取旗

在完成第二阶段优化后，再次使用 `profiling` 对目标 SQL 进行验证，结果如下：

```text
0.02429139s
```

与最初的约 **5.35 秒** 相比，性能提升非常明显，下降到了原来的不到百分之一。随后检查 `/flag` 文件，题目已自动判定通过并生成 flag：

```text
-rwxrwxrwx 1 root root 47 Apr 14 16:48 /flag
xctf{28a0679f83c14b2192d2423ac9a65e89eb7730e5}
```

这说明本题的判题逻辑并不是简单检查“是否建了索引”，而更可能是依据**实际查询耗时是否降低到阈值以内**来自动生成 `/flag`。从解题过程看，只有在**索引优化 + 统计信息校正**同时完成后，系统才认可当前优化结果。

## 八、完整复现命令

如果需要在同一环境中复现本题解法，可以按如下顺序执行。

```bash
mysql -uroot -proot -e "use test; \
create index idx_event_type_date_id on event_q(event_type, create_date, event_id); \
create index idx_staff_read_event on staff_event(staff_id, is_read, event_id); \
analyze table event_q, staff_event; \
set global use_stat_tables='PREFERABLY'; \
analyze table event_q persistent for all; \
analyze table staff_event persistent for all;"
```

随后可以使用下列命令验证执行计划与 flag：

```bash
mysql -uroot -proot -e "use test; \
explain select q.event_id, q.event_type, q.state, q.read_url, q.create_date, q.content, q.form_serial \
from event_q q, staff_event s \
where q.event_id = s.event_id \
  and q.content like '%权限%' \
  and q.event_type='2' \
  and q.create_date >= '2023-01-01' \
  and q.create_date <= '2023-08-12' \
  and s.is_read = 1 \
  and s.staff_id = 1 \
order by create_date desc;"

ls -l /flag
cat /flag
```

## 九、题目本质总结

本题表面上是 SQL 优化题，实际上考察的是**数据库执行计划分析能力**与**对优化器行为的理解**。如果只停留在“看条件就机械加索引”的层面，很容易卡在第一阶段：索引建好了，但计划仍不理想，判题也不通过。真正的突破点在于识别出：

第一，`content like '%权限%'` 无法成为主要索引过滤条件，因此必须从别的高选择性条件入手控制数据规模。第二，`staff_event` 的过滤条件选择性远强于 `event_q` 的日期与事件类型条件，因此连接顺序应当以 `staff_event` 为先。第三，在 MariaDB 中，仅有索引并不保证优化器选择最佳路径，必要时还需要通过 `ANALYZE TABLE PERSISTENT` 和 `use_stat_tables` 这类手段校正统计信息。

因此，本题的标准解并不是单一 SQL 命令，而是一套完整的**索引设计 + 统计信息修正 + 执行计划验证**的方法论。这也是后续在真实生产环境中处理慢查询时更接近工程实践的思路。
