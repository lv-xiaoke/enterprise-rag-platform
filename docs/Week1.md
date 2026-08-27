# Week 1：建立可信数据底座和可启动的数据库环境

当前仓库已经有一个能跑通“上传单个文本型 PDF → 切块 → Embedding → FAISS Top-3 检索 → LLM 回答并返回页码”的 Mini RAG，但它还不知道企业里有哪些设备、哪些文档有效，也无法在服务重启后保留索引。本周先不急着改 RAG 接口，而是把后续系统赖以判断“这是什么资料、能不能用、属于哪台设备、应该怎样评测”的数据基础准备好。完成本周后，仓库中应有一套口径统一、来源可追溯、能通过一致性检查的制造业演示数据集，以及一个可以启动并确认 pgvector 可用的 PostgreSQL 环境。

# 一、本周在整个项目中的位置

## 1. 当前真实起点

根据仓库现状，已经确认：

- `app/main.py` 使用全局 `rag_service`，每次成功上传都会替换上一份 PDF 的内存索引；
- `app/services/vector_store.py` 只保存 Chunk 文本、物理页码和 FAISS 向量，没有文档 ID、版本、设备类型或状态；
- `app/database.py` 的 SQLite 只保存普通 `/chat` 消息，不保存 RAG 文档或向量；
- `data/evaluation/questions.json` 是旧科研 PDF 的 12 道题，不能直接证明设备运维知识库的效果；
- 仓库有 `Dockerfile`，但没有 Compose 文件，也没有 PostgreSQL、pgvector、SQLAlchemy 或 Alembic 依赖；
- 仓库没有自动测试目录；README 中记录的是上一阶段 Mini RAG，而不是本月最终产品；
- 当前没有 `WeekN.md`，因此本文件是本月的 Week 1；
- Git 工作区已有计划与说明文档的未提交变化，学习过程中不能使用 `git add .`，也不能覆盖不属于当天任务的修改。

还有一个必须先解决的口径冲突：

| 项目 | 月度主计划 | 当前 `docs/项目范围说明.md` | 本周采用 |
| --- | --- | --- | --- |
| 设备类型 | 3 类 | 4 类，额外包含数控机床 | 3 类 |
| 资产数量 | 6 台 | 9 台，额外包含 P-03、CNC-01、CNC-02 | 6 台 |
| 固定评测题 | 30 道 | 不少于 50 道 | 30 道 |

`docs/制造企业设备运维知识库一月计划.md` 是本月最高依据，所以 Week 1 必须先把范围说明改回三类设备、六台资产和 30 道题。否则后续文档、工单、数据库字段和评测会同时存在两套标准。

## 2. 本周在月度主线中的位置

```text
本周输入
现有 Mini RAG 代码 + 月度主计划 + 尚未统一的项目范围
        ↓
统一业务边界和 ID 规则
        ↓
建立元数据目录、文档模板和来源登记
        ↓
编写 15 份资料版本 + 20 条虚构工单
        ↓
建立 30 道评测题骨架并运行数据一致性检查
        ↓
启动 PostgreSQL + pgvector 环境
        ↓
本周输出
数据集 v0.1 + 可验证的数据库环境
        ↓
下周使用这些输入设计数据库表、迁移、多文档入库和版本过滤
```

本周处于整个月主线的第一段：

```text
【可信资料与来源登记】
→ PostgreSQL + pgvector 数据模型与迁移
→ 多文档入库、版本过滤
→ 引用、拒答与评测
→ 页面、部署与演示
```

如果第一段的数据边界不稳定，第二周的数据表就只能凭想象设计；如果没有旧版、当前版和无答案题，第三周也无法证明版本过滤与拒答真的有效。

## 3. 本周明确不做

- 不把现有 FAISS 替换为 pgvector；本周只准备数据库运行环境；
- 不接入 SQLAlchemy、Alembic 或 PostgreSQL 驱动；这些属于 Week 2；
- 不改造 `/upload`、`/rag/chat` 或 Pydantic 响应模型；
- 不制作管理页面、权限系统、异步任务、OCR、Reranker 或混合检索；
- 不下载并提交未经许可的厂商手册、标准全文或真实企业资料；
- 不重写 README 的完整产品说明，README 的最终整理放在 Week 4；
- 不为了凑数量写互相矛盾、没有来源记录或缺少安全条件的资料。

# 二、本周完成后的整体效果

## 1. 用一个场景理解本周价值

做之前，系统只能回答“刚刚上传的那一份 PDF”中的内容。即使上传了一份空压机规程，系统也不知道它适用于 AC-01 还是 AC-02，不知道它是旧版还是当前版，更无法判断某条维修工单是否与规程中的设备编号一致。

做完之后，仓库会先拥有一个清楚的数据世界：启明精工是虚构企业；范围只包含 AC-01、AC-02、P-01、P-02、CV-01、CV-02；每份资料都有稳定 ID、版本、生效日期、状态和来源；20 条工单只能引用这六台设备；30 道题明确要查哪类资料。第二周设计数据库时，字段不再是凭空猜测，而是从这些真实样例中提炼出来。

## 2. 本周交付物

| 交付物 | 预期路径 | 后续用途 |
| --- | --- | --- |
| 统一后的项目范围 | `docs/项目范围说明.md` | 约束设备、用户、题目数量和安全边界 |
| 数据说明、命名规范和文档模板 | `data/manufacturing_demo/README.md`、`templates/` | 让 15 份资料遵循同一结构 |
| 来源与文档元数据目录 | `source_registry.csv`、`metadata/documents.csv` | 支撑可追溯来源、版本和状态过滤 |
| 15 份资料版本 | `data/manufacturing_demo/documents/` | Week 2 多文档入库的输入 |
| 20 条虚构维修工单 | `data/manufacturing_demo/work_orders/work_orders_v0.1.csv` | 跨文档问题与一致性检查样例 |
| 30 道评测题骨架 | `data/manufacturing_demo/evaluation/questions_v0.1.json` | Week 3 标注证据并运行固定评测 |
| 数据验证脚本 | `scripts/validate_manufacturing_dataset.py` | 重复检查数量、ID、版本和引用关系 |
| 数据库运行环境 | `compose.yaml`、`.env.example` | Week 2 接入 PostgreSQL 和 pgvector |

本周资料统一使用便于 Git 审查的 Markdown 和 CSV/JSON 作为源文件。`page` 与 `chunk_id` 是文档进入解析和切块流程后才产生的 Chunk 级信息，不要在源文档中虚构物理页码。后续需要 PDF 演示时，再从已审核的源文件生成可追溯 PDF。

# 三、本周知识地图与关键概念

## 1. 知识依赖关系

```text
项目范围
决定有哪些设备和问题
      ↓
稳定 ID、元数据和文档状态
决定资料怎样被识别与过滤
      ↓
来源登记、模板和安全规则
决定资料是否可信、是否能提交
      ↓
文档与工单
构成知识库真正要检索的内容
      ↓
固定评测题
提前规定以后怎样证明系统有效
      ↓
PostgreSQL + pgvector
为下周持久保存这些对象提供环境
```

## 2. 数据契约：先统一“世界观”，再写数据

**它是什么：** 数据契约就是项目中大家共同遵守的名词、编号、字段和取值规则。例如，`AC-01` 永远表示同一台虚构空压机，`active` 永远表示当前允许参与检索的文档版本。

**为什么需要：** 如果范围说明有 P-03，设备台账却没有 P-03，工单又引用了 P-03，那么系统即使检索正确，也会给出业务上无法核对的答案。

**影响哪里：** 它会直接决定 CSV 字段、数据库表、API 过滤条件、评测题和演示脚本。

**怎样证明理解：** 你应能解释：“为什么增加一台设备不能只在一条工单中临时写进去，而必须同步更新范围、台账、资料和评测？”

## 3. 文档元数据与版本生命周期

**它是什么：** 文档正文像书的内容，元数据像书脊和档案卡。`document_id` 表示“这是哪一份制度”，`version` 表示“它的哪个版本”，`status` 表示“当前是否允许使用”。同一个 `document_id` 可以有 v1.0 和 v1.1 两条版本记录。

**为什么需要：** 用户问当前点检要求时，系统必须排除已经停用的 v1.0，只引用 `active` 的 v1.1。

**影响哪里：** Week 1 的文件名和 `documents.csv` 会成为 Week 2 的文档表、版本表和检索过滤条件，也会成为 Week 3 版本题的证据。

**怎样证明理解：** 你应能说明 `document_id`、`version`、`effective_date` 和 `status` 各自解决什么问题，并举出“同一文档两个版本”的例子。

## 4. 来源登记不等于拥有再分发权

**它是什么：** `source_registry.csv` 是知识来源的账本，记录标题、发布机构、URL、访问日期、许可/条款、采用的知识点以及是否允许再分发。

**为什么需要：** “网页能打开”只说明可以访问，不说明可以把完整手册复制到公开仓库。项目可以阅读官方资料后用自己的语言编写虚构规程，但不能默认拥有原文件版权。

**影响哪里：** 它决定仓库能提交哪些内容、回答引用的背景是否可追溯，也影响最终 README 和案例报告能否公开。

**怎样证明理解：** 给定一份厂商 PDF，你应能区分“可以阅读和提炼知识”与“可以把原 PDF 重新发布”是两次不同判断。

## 5. 虚构数据也必须保持一致

**它是什么：** `synthetic/demo` 表示企业、资产、工单和事件是为了教学人为构造的，不对应真实客户。但虚构不等于随意：编号、时间、故障原因、引用版本和安全步骤仍要自洽。

**为什么需要：** 一个面试演示如果同一设备在台账中是离心泵、在工单中却成了输送机，会直接失去可信度。

**影响哪里：** 一致性规则会进入验证脚本、评测题、数据库外键和最终演示。

**怎样证明理解：** 你应能列出一条工单至少需要和台账、文档版本、日期以及安全要求做哪四类核对。

## 6. 评测先于优化

**它是什么：** 固定评测集像考试卷。先固定问题类型、预期证据和是否可回答，后面改变 Chunk、Top-k 或阈值时才有同一把尺子。

**为什么需要：** 只挑系统刚好能答的问题做演示，无法证明检索、版本过滤和拒答能力。

**影响哪里：** Week 1 先定 30 道题骨架；Week 3 再补标准答案、证据定位，比较至少两组检索参数。

**怎样证明理解：** 你应能说明为什么“无答案题”和“版本题”不能等系统写完后再临时添加。

## 7. PostgreSQL、pgvector 与 Compose 的分工

**它是什么：** PostgreSQL 保存文档、版本、状态和 Chunk 等业务数据；pgvector 是 PostgreSQL 的向量扩展；Compose 用一个配置文件描述数据库容器、端口、健康检查和持久化卷。

**为什么需要：** 当前 FAISS 索引只在 Python 进程内，重启即丢失。下周把向量与业务元数据放进同一数据库后，才能同时做相似度检索和 `active` 版本过滤。

**影响哪里：** Week 1 只确认环境能启动、vector 扩展可用；Week 2 才设计表、执行迁移和接入代码。

**怎样证明理解：** 你应能解释“启动 pgvector 容器”和“应用已经完成持久化改造”为什么不是同一件事。

## 8. 容易混淆的概念

| 容易混淆 | 正确区别 |
| --- | --- |
| `document_id` 与文件名 | ID 是稳定业务身份；文件名只是仓库中的载体 |
| 文档 `active/inactive` 与处理 `completed/failed` | 前者决定能否检索，后者说明解析任务是否成功 |
| 登记了来源与允许再分发 | 登记来源不自动产生复制和公开发布权 |
| 相似度高与回答正确 | 相似度只表示向量接近，仍需核对原文、版本与安全条件 |
| 数据集文件存在与学习完成 | 只有你能解释设计并通过验证，才算真正完成 |

# 四、本周进度看板

- [ ] 项目范围已统一为三类设备、六台资产和 30 道评测题。
- [ ] 已建立数据集目录、命名规则、元数据字典和文档模板。
- [ ] `source_registry.csv` 记录了采用知识点、许可判断和再分发边界。
- [ ] `documents.csv` 中有 15 个版本记录，且旧版与当前版状态清楚。
- [ ] 15 份 Markdown 资料均标记为 `synthetic/demo`，并保留必要安全条件。
- [ ] `work_orders_v0.1.csv` 有 20 条工单，只引用六台合法资产和已登记文档版本。
- [ ] 30 道题按 8/6/6/4/3/3 的类型分布建立骨架，至少 10 道能定位明确证据。
- [ ] 数据验证脚本能重复运行，并以零错误结束。
- [ ] PostgreSQL + pgvector 容器能健康启动，且可以查询到 vector 扩展。
- [ ] 已留下本周讲解素材，并能说明本周成果怎样进入 Week 2。

# 五、Day 1～Day 7 的详细安排

## Day 1：统一项目范围和数据契约

### 今天在整周中的作用

今天先解决范围冲突。输入是月度主计划、现有范围说明和旧 Mini RAG 事实；输出是一份唯一可信的范围说明与数据集总纲。Day 2 的元数据表、Day 3～Day 5 的文档和工单都会依赖今天确定的设备 ID 与题目数量。

### 先理解再动手

范围说明不是“项目介绍文案”，而是后续数据的边界。主计划只覆盖三类设备，是为了让 14 小时左右的 Week 1 能把资料做一致，而不是把精力分散到数控机床的新故障体系。今天最重要的学习不是删掉几个名称，而是理解：业务范围会一路传导到数据表、检索过滤、评测与演示。

常见错误是只改文档中的“四类”为“三类”，却留下 P-03、CNC 典型问题或 50 道题要求。这样表面改了范围，实际仍有两套口径。

### 核心任务

1. 在项目根目录确认当前工作区，不处理或丢弃已有修改：

```powershell
git status --short
git log -5 --oneline
```

当前工作区并非干净状态。今天及本周都不要使用 `git add .`、`git checkout --` 或任何批量清理命令。

2. 对照阅读：

```powershell
Get-Content .\docs\制造企业设备运维知识库一月计划.md
Get-Content .\docs\项目范围说明.md
```

3. 修改 `docs/项目范围说明.md`：

- 设备固定为螺杆式空气压缩机、离心泵、皮带输送机；
- 资产固定为 AC-01、AC-02、P-01、P-02、CV-01、CV-02；
- 删除数控机床、P-03 及相关典型问题；
- 固定评测集改为 30 道；
- 保留管理员、维修工程师、生产/安全查看者三类业务视角，但不承诺本月实现完整权限；
- 保留虚构数据、来源许可、挂牌上锁、断电泄压和无依据拒答边界。

4. 创建数据集目录和总说明：

```powershell
$datasetDirs = @(
    '.\data\manufacturing_demo\metadata',
    '.\data\manufacturing_demo\templates',
    '.\data\manufacturing_demo\documents\common',
    '.\data\manufacturing_demo\documents\safety',
    '.\data\manufacturing_demo\documents\air_compressor',
    '.\data\manufacturing_demo\documents\centrifugal_pump',
    '.\data\manufacturing_demo\documents\belt_conveyor',
    '.\data\manufacturing_demo\work_orders',
    '.\data\manufacturing_demo\evaluation'
)

foreach ($datasetDir in $datasetDirs) {
    New-Item -ItemType Directory -Force -Path $datasetDir | Out-Null
}
```

创建 `data/manufacturing_demo/README.md`，写清：

- 数据集用途与 `synthetic/demo` 声明；
- 企业、知识库和六台资产的稳定 ID；
- 目录结构和文件命名格式；
- 文档级字段与 Chunk 级字段的区别；
- v1.0 旧版、v1.1 当前版的状态规则；
- 公开来源只用于提炼知识，未确认许可的原文件不进入仓库；
- 本周数量目标：15 份资料版本、20 条工单、30 道题。

建议固定知识库 ID 为 `kb-qiming-maintenance-demo`。文件名采用小写英文和版本号，例如 `ac_operation_inspection_v1.0.md`，避免以后在 API、容器和脚本中处理多套命名规则。

### 验证方法

验证范围冲突是否清除：

```powershell
Select-String `
    -Path .\docs\项目范围说明.md `
    -Pattern 'CNC-|P-03|50 道|四类|九台'
```

预期没有匹配。再确认合法资产与题目数量存在：

```powershell
Select-String `
    -Path .\docs\项目范围说明.md,.\data\manufacturing_demo\README.md `
    -Pattern 'AC-01|AC-02|P-01|P-02|CV-01|CV-02|30 道|synthetic'
```

如果旧范围词仍出现，先看它是否只是“本月不做”的说明；若它仍被列为第一版资产，就继续修正。

最后只检查今天涉及的差异：

```powershell
git diff -- .\docs\项目范围说明.md .\data\manufacturing_demo\README.md .\docs\Week1.md
git diff --check
```

### 当天可见产出

- 更新后的 `docs/项目范围说明.md`；
- `data/manufacturing_demo/README.md`；
- 数据集目录骨架；
- 一套可口头解释的三类设备、六台资产、30 道题的数据契约。

### 与明天的衔接

明天会把今天的业务边界翻译成 CSV 字段、15 个文档版本记录和统一模板。没有今天的稳定 ID，明天的元数据表无法判断什么值合法。

### 录屏与 Git

保留 30～60 秒素材：展示主计划与旧范围冲突，再展示统一后的六台资产，口播“范围不是文案，它会决定数据库、检索和评测”。验证无误后再选择性暂存：

```powershell
git status --short
git add -- .\docs\Week1.md .\docs\项目范围说明.md .\data\manufacturing_demo\README.md
git diff --cached
git commit -m "docs: align manufacturing demo scope"
```

如果暂存区出现提示词、月计划或其他已有修改，先取消那些路径的暂存，不要把来源不明的改动混进本次提交。

### 当天完成清单

- [ ] 我能解释为什么主计划必须是本月唯一口径。
- [ ] 范围已统一为三类设备、六台资产和 30 道题。
- [ ] 数据集 README 写清 ID、目录、版本和安全边界。
- [ ] 冲突关键词检查没有发现残留的第一版资产。
- [ ] 我只检查并提交了今天明确涉及的路径。

## Day 2：建立来源账本、元数据目录和公共资料

### 今天在整周中的作用

昨天确定“知识库中允许有什么”，今天确定“每份资料怎样被识别、怎样说明来源”。输出是模板、来源登记、15 个版本记录，以及企业说明、设备台账和两份安全制度。后面三天所有设备资料都从同一个模板出发。

### 先理解再动手

文档内容和文档元数据解决不同问题。正文回答“空压机高温先检查什么”，元数据回答“这份内容属于哪类设备、哪个版本、当前是否有效”。RAG 的向量检索只擅长找语义相近的文本，不能替代明确的版本和状态过滤。

来源登记也不是装饰。每条资料都要能回答：知识参考自哪里、采用了什么、是否改写、原文件能否公开。许可不清楚时，最安全的做法是只提交自己的摘要与来源链接，不提交第三方原件。

### 核心任务

1. 创建 `data/manufacturing_demo/source_registry.csv`，至少包含：

```text
source_id,title,publisher,url,accessed_at,license_or_terms,knowledge_used,redistribution_allowed,local_copy_committed,notes
```

先登记一条项目自编数据规则来源，再从政府部门、厂商官方网站、开放课程或许可清楚的资料中查找安全、空压机、离心泵和输送机知识来源。优先登记 6～10 条高质量来源，不追求数量。`redistribution_allowed` 只使用 `yes/no/unknown`；没有明确证据时写 `unknown`，不提交原文件。

2. 创建 `data/manufacturing_demo/metadata/documents.csv`，每一行表示一个“文档版本”，字段至少包括：

```text
knowledge_base_id,document_id,version,title,document_type,equipment_type,equipment_ids,effective_date,status,source_ids,file_path,synthetic
```

规划 15 行版本记录：

- 公共与安全资料 4 行；
- 空压机操作/点检 v1.0 与 v1.1、故障指南、保养计划，共 4 行；
- 离心泵操作/点检、故障指南、保养计划，共 3 行；
- 输送机操作/点检 v1.0 与 v1.1、故障指南、保养计划，共 4 行。

空压机和输送机的 v1.0 与 v1.1 使用相同 `document_id`。v1.0 标记 `inactive`，v1.1 标记 `active`；其余当前资料标记 `active`。不要把“文件处理成功与否”混入这里，`pending/processing/completed/failed` 是 Week 2 的处理状态。

3. 创建 `data/manufacturing_demo/templates/document_template.md`，模板包含：

- `synthetic/demo` 醒目标识；
- 文档 ID、版本、状态、生效日期、设备类型、适用设备和来源 ID；
- 目的与适用范围；
- 操作、点检或故障知识正文；
- 断电、泄压、挂牌上锁、人员资质和升级处理条件；
- 已知限制与禁止事项；
- 版本变更说明。

4. 根据模板完成四份简短但完整的公共资料：

```text
documents/common/company_data_statement_v0.1.md
documents/common/equipment_registry_v1.0.md
documents/safety/loto_safety_v1.0.md
documents/safety/general_maintenance_safety_v1.0.md
```

设备台账只登记 AC-01、AC-02、P-01、P-02、CV-01、CV-02。不要使用真实品牌、序列号、人员姓名或企业地址。

### 验证方法

检查文档目录行数和版本唯一性：

```powershell
$documentCatalog = Import-Csv .\data\manufacturing_demo\metadata\documents.csv
$documentCatalog.Count

$documentCatalog |
    Group-Object { "$($_.document_id)|$($_.version)" } |
    Where-Object Count -gt 1
```

预期第一条输出 `15`，第二条没有输出。检查状态和非法资产：

```powershell
$validEquipmentIds = @('AC-01','AC-02','P-01','P-02','CV-01','CV-02')

$documentCatalog | Where-Object {
    $_.status -notin @('draft','active','inactive')
}

$documentCatalog | Where-Object {
    $_.equipment_ids -and
    (($_.equipment_ids -split ';') | Where-Object { $_ -notin $validEquipmentIds })
}
```

两次检查都应无输出。再人工抽查 `source_registry.csv`：URL 可访问不等于 `redistribution_allowed=yes`，许可不清楚的行必须是 `unknown` 或 `no`。

### 当天可见产出

- 一份来源账本；
- 一份包含 15 个版本记录的文档目录；
- 一个可复用模板；
- 企业说明、六台设备台账和两份通用安全制度。

### 与明天的衔接

明天会用模板制作空压机资料。`documents.csv` 已经规定文件名、ID 和版本，所以写正文时不再临时发明字段。

### 录屏与 Git

录制来源登记表和 v1.0/v1.1 两行元数据，口播“原文负责回答，元数据负责决定能不能被检索”。检查后提交明确路径：

```powershell
git status --short
git diff -- .\data\manufacturing_demo
git diff --check
git add -- .\data\manufacturing_demo
git diff --cached
git commit -m "data: add manufacturing dataset schema and common docs"
```

### 当天完成清单

- [ ] 我能区分来源登记、知识引用和再分发许可。
- [ ] 文档目录正好有 15 个唯一的版本记录。
- [ ] 同一文档的 v1.0 与 v1.1 共用稳定 `document_id`。
- [ ] 四份公共资料均有虚构标识和必要安全边界。
- [ ] 元数据检查没有非法状态、重复版本或额外资产。

## Day 3：完成空压机资料和 6 条工单

### 今天在整周中的作用

今天把模板首次用于一种真实设备知识域。输出是空压机的旧版、当前版、故障指南、保养计划和 6 条工单。它会验证昨天的元数据是否真的够用，并为 Day 6 的事实题、流程题、版本题和跨文档题提供材料。

### 先理解再动手

“故障指南”应该给出安全前提、可能原因和检查顺序，不是让系统自动下发维修指令。工单则是已经发生过的虚构事件记录，它可以说明某台设备曾出现什么症状、经过什么检查，但不能自动取代当前有效规程。

今天还要理解版本关系：v1.0 可以保留用于历史审计，但状态是 `inactive`；v1.1 是当前版本，必须明确写出替代关系和改变了什么。常见错误是只改文件名中的版本号，正文内容和生效日期却完全相同，这样无法形成有意义的版本题。

### 核心任务

完成：

```text
documents/air_compressor/ac_operation_inspection_v1.0.md
documents/air_compressor/ac_operation_inspection_v1.1.md
documents/air_compressor/ac_fault_guide_v1.0.md
documents/air_compressor/ac_maintenance_plan_v1.0.md
```

建议让 v1.1 只包含一项清楚、可评测且不涉及危险参数的变化，例如增加开机前安全确认或调整点检记录要求。v1.1 必须写明替代 v1.0，`documents.csv` 中 v1.0 为 `inactive`、v1.1 为 `active`。

正文覆盖高温、压力不足、滤芯、润滑和日常点检，但不要编造精确温度、压力阈值或扭矩值。没有可靠来源支撑的具体参数应写成“以当前有效制造商资料和现场制度为准”。高风险步骤必须要求停机、断电、泄压、挂牌上锁并由具备资质人员处理。

在 `work_orders/work_orders_v0.1.csv` 中创建表头和 6 条空压机工单。字段至少包括：

```text
work_order_id,event_date,equipment_id,symptom,cause,action,safety_steps,related_document_id,related_version,result,synthetic
```

让 AC-01、AC-02 都有记录，至少一台出现重复故障。历史日期早于 v1.1 生效日的工单可以引用 v1.0，之后的工单应引用 v1.1；工单内容必须与故障指南和保养计划一致。

### 验证方法

```powershell
$orders = Import-Csv .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv
$orders.Count
$orders | Group-Object equipment_id | Select-Object Name,Count

$orders | Where-Object {
    $_.equipment_id -notin @('AC-01','AC-02') -or
    $_.synthetic -ne 'true' -or
    -not $_.safety_steps
}
```

预期总数为 `6`，AC-01 与 AC-02 都出现，最后一条检查无输出。再核对版本状态：

```powershell
Import-Csv .\data\manufacturing_demo\metadata\documents.csv |
    Where-Object document_id -eq 'DOC-AC-OP-001' |
    Select-Object document_id,version,effective_date,status,file_path
```

预期能看见同一 ID 的 v1.0 `inactive` 和 v1.1 `active`。如果实际采用了不同 ID，以你的数据契约为准，但必须保证两个版本属于同一业务文档。

### 当天可见产出

- 4 份空压机资料版本；
- 6 条空压机虚构工单；
- 一组能用于验证旧版过滤和重复故障分析的样例。

### 与明天的衔接

明天会把同样的数据契约应用到离心泵。若今天发现模板缺字段，应先更新模板和 `documents.csv`，不能只在空压机文件里临时增加私有格式。

### 录屏与 Git

展示 v1.0/v1.1 的差异和一条跨日期工单，避免录到本地隐私路径或浏览器账户。验证后：

```powershell
git diff -- .\data\manufacturing_demo\documents\air_compressor .\data\manufacturing_demo\work_orders .\data\manufacturing_demo\metadata\documents.csv
git diff --check
git add -- .\data\manufacturing_demo\documents\air_compressor .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv .\data\manufacturing_demo\metadata\documents.csv
git diff --cached
git commit -m "data: add air compressor docs and work orders"
```

### 当天完成清单

- [ ] 我能解释规程、故障指南、保养计划和工单的不同职责。
- [ ] 空压机四个版本文件与文档目录一一对应。
- [ ] v1.0 与 v1.1 有真实可解释的差异和正确状态。
- [ ] 6 条工单覆盖 AC-01、AC-02，并保留安全步骤。
- [ ] 工单日期、引用版本和资料内容没有明显矛盾。

## Day 4：完成离心泵资料和累计 13 条工单

### 今天在整周中的作用

昨天验证了模板能表达版本关系，今天验证同一结构能否复用于另一类设备。输出是离心泵的三份当前有效资料和 7 条新工单，使工单累计达到 13 条。Day 6 将用它们设计故障诊断题与跨文档题。

### 先理解再动手

复用模板不等于复制空压机内容后替换设备名。离心泵的知识主题是汽蚀、泄漏、振动、密封和启停；其症状、原因与检查顺序必须构成因果链。资料可以说明“先确认工况和安全条件，再按顺序检查”，但不能在缺少现场信息时断言唯一故障原因。

常见错误是让所有工单都得到相同原因，这会让跨文档分析失去意义。应该保留少量重复故障用于统计，同时让不同症状对应不同、但有来源支持的检查路径。

### 核心任务

完成：

```text
documents/centrifugal_pump/pump_operation_inspection_v1.0.md
documents/centrifugal_pump/pump_fault_guide_v1.0.md
documents/centrifugal_pump/pump_maintenance_plan_v1.0.md
```

正文覆盖汽蚀、泄漏、振动、密封和启停流程，并清楚写明：涉及拆卸、带压系统或电气检查时必须停机、隔离能量、确认泄压并由合格人员处理。

向 `work_orders_v0.1.csv` 增加 7 条离心泵工单，使总数达到 13。P-01、P-02 都要出现，至少形成一组“同一设备重复症状”的记录，方便后续跨文档问题检查保养计划是否覆盖相关原因。

### 验证方法

```powershell
$orders = Import-Csv .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv
$orders.Count
$orders | Group-Object equipment_id | Select-Object Name,Count

$pumpOrders = $orders | Where-Object equipment_id -in @('P-01','P-02')
$pumpOrders.Count
$pumpOrders | Where-Object {
    -not $_.related_document_id -or
    -not $_.related_version -or
    -not $_.safety_steps
}
```

预期总数 `13`，其中离心泵 `7` 条，P-01 与 P-02 都出现，最后一条无输出。人工抽查至少两条工单，确认症状、原因、处理和引用文档能在三份泵资料中相互解释。

### 当天可见产出

- 3 份离心泵资料；
- 7 条离心泵工单，工单累计 13 条；
- 一组可用于故障诊断和重复故障分析的样例。

### 与明天的衔接

明天完成输送机资料和剩余 7 条工单，并对六台设备做第一次全量一致性检查。

### 录屏与 Git

展示一条振动工单如何对应故障指南的检查顺序。验证后只暂存本日路径：

```powershell
git diff -- .\data\manufacturing_demo\documents\centrifugal_pump .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv
git diff --check
git add -- .\data\manufacturing_demo\documents\centrifugal_pump .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv
git diff --cached
git commit -m "data: add pump docs and work orders"
```

### 当天完成清单

- [ ] 我能解释症状、可能原因和检查顺序之间的关系。
- [ ] 三份泵资料的元数据与文档目录一致。
- [ ] 新增 7 条工单，总数达到 13。
- [ ] P-01、P-02 都有记录，并存在可解释的重复故障。
- [ ] 抽查工单能在当前有效资料中找到依据。

## Day 5：完成输送机资料、20 条工单和数据集 v0.1

### 今天在整周中的作用

今天补齐第三类设备，使资料与工单第一次形成完整数据集。输出是输送机旧版、当前版、故障指南和保养计划，以及剩余 7 条工单。完成后，Day 6 才能在完整资料上设计 30 道题并写自动验证。

### 先理解再动手

输送机资料需要同时处理跑偏、打滑、异响、张紧和急停检查。急停属于安全保护，不能把“复位急停”写成绕过安全检查的快速恢复步骤。任何涉及张紧、护罩拆卸或运动部件的操作，都要先停机、隔离能量并确认设备不会意外启动。

今天的重点还包括跨文件一致性。单份文档写得通顺不够，必须检查台账、资料目录、正文和工单是否都使用相同设备 ID、版本与日期。

### 核心任务

完成：

```text
documents/belt_conveyor/conveyor_operation_inspection_v1.0.md
documents/belt_conveyor/conveyor_operation_inspection_v1.1.md
documents/belt_conveyor/conveyor_fault_guide_v1.0.md
documents/belt_conveyor/conveyor_maintenance_plan_v1.0.md
```

让 v1.1 对急停检查或开机前确认做一项明确更新，v1.0 为 `inactive`、v1.1 为 `active`。不要用新版补丁去省略完整安全条件；v1.1 应能独立表达当前有效要求。

向工单 CSV 增加 7 条 CV-01、CV-02 记录，使总数达到 20。至少包含跑偏、打滑和异常噪声，并保留一组重复事件。完成后从文档目录逐行检查 15 个 `file_path` 是否都真实存在。

### 验证方法

```powershell
$catalog = Import-Csv .\data\manufacturing_demo\metadata\documents.csv
$orders = Import-Csv .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv
$validEquipmentIds = @('AC-01','AC-02','P-01','P-02','CV-01','CV-02')

$catalog.Count
$orders.Count
$orders | Group-Object equipment_id | Select-Object Name,Count

$catalog | Where-Object {
    -not (Test-Path (Join-Path '.\data\manufacturing_demo' $_.file_path))
}

$orders | Where-Object {
    $_.equipment_id -notin $validEquipmentIds -or
    $_.synthetic -ne 'true' -or
    -not $_.related_document_id -or
    -not $_.safety_steps
}
```

预期文档目录 `15` 行、工单 `20` 行、六台设备都有记录，最后两项检查没有输出。如果 `file_path` 已写成从仓库根目录开始的路径，相应调整 `Join-Path`，但整个目录只能采用一种口径。

再抽查 5 份资料：公共、安全、空压机旧版/新版、泵、输送机中至少覆盖 5 类，逐份说明设备类型、版本、状态、来源和安全条件。

### 当天可见产出

- 4 份输送机资料版本；
- 20 条完整虚构工单；
- 15 份资料版本全部落盘的数据集 v0.1；
- 第一轮人工一致性检查记录。

### 与明天的衔接

明天不再扩充资料数量，而是把数据集转成一张固定“考试卷”，并让脚本自动检查今天手工核对的规则。

### 录屏与 Git

展示 15 个文档记录、20 条工单分布和输送机 v1.0/v1.1 状态。验证后：

```powershell
git diff -- .\data\manufacturing_demo
git diff --check
git add -- .\data\manufacturing_demo\documents\belt_conveyor .\data\manufacturing_demo\work_orders\work_orders_v0.1.csv .\data\manufacturing_demo\metadata\documents.csv
git diff --cached
git commit -m "data: complete manufacturing dataset v0.1"
```

### 当天完成清单

- [ ] 输送机四个版本文件与目录一致。
- [ ] v1.1 能独立表达当前有效安全要求，没有绕过急停或护罩。
- [ ] 工单总数正好为 20，且只使用六台合法资产。
- [ ] 15 个 `file_path` 都能定位到真实文件。
- [ ] 我人工抽查了 5 份资料并能解释来源、版本和状态。

## Day 6：建立 30 道评测题骨架和自动数据检查

### 今天在整周中的作用

前五天得到数据，今天规定以后怎样证明系统做对了。输出是一份固定问题骨架和一个可重复运行的验证脚本。它们会在 Week 2 检查入库与版本过滤，在 Week 3 补齐标准答案、证据位置并比较检索参数。

### 先理解再动手

旧 `data/evaluation/questions.json` 的 12 道题只适用于科研测试 PDF，可以借鉴字段结构，但不能覆盖或改名。制造业题集必须独立保存，并且问题类型要覆盖单文档事实、流程、故障、跨文档、版本和无答案。

题目骨架不是让模型提前生成漂亮答案，而是明确“这个问题是否应该回答、应该依据哪些文档”。无答案题尤其重要：它验证系统能否停止，而不是验证模型能否凭常识编一个合理故事。

### 核心任务

1. 创建 `data/manufacturing_demo/evaluation/questions_v0.1.json`，顶层记录数据集版本、知识库 ID、创建目的和 `cases`。每个 case 至少包含：

```text
id,category,question,answerable,expected_document_ids,expected_points,evidence_note,notes
```

严格使用下面的 30 道分布：

| 类型 | 数量 | 本周要确定什么 |
| --- | ---: | --- |
| `single_document_fact` | 8 | 明确来自一份当前有效资料的事实 |
| `procedure` | 6 | 安全前提与步骤顺序 |
| `fault_diagnosis` | 6 | 症状、可能原因和检查顺序 |
| `cross_document` | 4 | 台账、规程、保养计划和工单的组合 |
| `version` | 3 | 只接受当前有效版本或能识别历史版本 |
| `unanswerable` | 3 | 资料缺失、越界控制或无可靠参数时拒答 |

至少 10 道可回答题填写明确的 `expected_document_ids` 和 `evidence_note`。3 道无答案题的数组应为空，并写清拒答理由。不要编造页码；页码在后续生成 PDF 并完成解析后再标注。

2. 创建 `scripts/validate_manufacturing_dataset.py`，仅使用 Python 标准库读取 CSV、JSON 和 Markdown。检查：

- 文档版本数为 15、`document_id + version` 唯一、文件存在；
- 状态只属于 `draft/active/inactive`，每个有多版本的文档只有一个 `active`；
- 所有 `source_ids` 都能在来源表找到；
- 工单数为 20、ID 唯一、设备 ID 合法、引用的文档版本存在；
- 工单都有 `synthetic=true` 和安全步骤；
- 题目数为 30、ID 唯一、类型分布正确；
- 题目引用的文档 ID 存在，无答案题不伪造证据；
- 出错时打印具体文件与记录 ID，并以非零状态退出；成功时打印数量摘要。

不要把验证脚本写成自动“修复”数据的程序。验证器只报告问题，避免静默改坏人工资料。

### 验证方法

先检查 JSON 能被解析和类别数量：

```powershell
$evaluation = Get-Content `
    .\data\manufacturing_demo\evaluation\questions_v0.1.json `
    -Raw |
    ConvertFrom-Json

$evaluation.cases.Count
$evaluation.cases | Group-Object category | Select-Object Name,Count
```

预期总数为 `30`，类别分别是 8、6、6、4、3、3。然后运行：

```powershell
python .\scripts\validate_manufacturing_dataset.py
```

成功标准是退出码为 0，并出现类似 `documents=15, work_orders=20, questions=30, errors=0` 的摘要。这个文本只是预期接口，由你在脚本中实现；没有实际运行成功前，不要在周记录中写“已通过”。

如果失败，一次只修复一个明确错误，再重新运行。不要让脚本忽略未知设备、缺失来源或无效版本来换取绿色结果。

### 当天可见产出

- 30 道固定问题骨架；
- 至少 10 道有明确文档证据的可回答题；
- 一个可以重复运行的数据验证脚本；
- 一次真实的验证结果或清楚记录的失败项。

### 与明天的衔接

明天启动数据库环境，并用今天的验证结果做周验收。Week 2 会把文档、版本和 Chunk 映射成数据库表；今天的字段和错误规则就是数据模型的输入。

### 录屏与 Git

录制验证脚本从运行到输出摘要的过程，并展示一个版本题和一个无答案题。验证后：

```powershell
git diff -- .\data\manufacturing_demo\evaluation .\scripts\validate_manufacturing_dataset.py
git diff --check
git add -- .\data\manufacturing_demo\evaluation\questions_v0.1.json .\scripts\validate_manufacturing_dataset.py
git diff --cached
git commit -m "test: add manufacturing dataset validation and questions"
```

### 当天完成清单

- [ ] 我能解释为什么评测题要在检索优化前固定。
- [ ] 30 道题的类别数量严格符合主计划。
- [ ] 至少 10 道题能定位到明确资料证据。
- [ ] 3 道无答案题没有伪造文档依据。
- [ ] 验证脚本真实运行，并清楚报告成功或具体错误。

## Day 7：启动 pgvector 环境并完成整周验收

### 今天在整周中的作用

今天不再增加资料类型。核心是确认 Week 2 所需的数据库基础可用，并对全周成果做总体验收、补漏和复盘。输出是 Compose 配置、pgvector 可用证据、周总结和视频素材。

### 先理解再动手

启动一个数据库容器只证明“基础设施可用”，不代表应用已经持久化。当前 Python 依赖中还没有 SQLAlchemy、Alembic、PostgreSQL 驱动或 pgvector Python 包，`app/main.py` 也仍使用内存 FAISS。这些都不是错误，而是 Week 1 与 Week 2 的明确边界。

Compose 中的命名卷会把数据库文件保存在容器生命周期之外；`pgvector` 扩展让 PostgreSQL 认识向量类型和距离运算。今天只检查扩展可用，不创建正式业务表，也不执行应用迁移。

### 核心任务

1. 先确认本机环境，不安装或升级任何东西：

```powershell
docker --version
docker compose version
```

如果命令不存在或 Docker Desktop 未运行，记录为明确卡点，不要假装数据库已经验证，也不要临时改成另一套数据库方案。

2. 创建 `.env.example`，只写变量名和安全占位值，不写真实模型密钥：

```text
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
POSTGRES_PASSWORD=replace-with-local-development-password
```

项目已有被 Git 忽略的 `.env`。如果需要，在现有 `.env` 末尾手工增加 `POSTGRES_PASSWORD`；不要覆盖、打印、复制或提交已有内容。

3. 创建根目录 `compose.yaml`，第一版只包含数据库服务：

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: enterprise_rag
      POSTGRES_USER: rag_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag_user -d enterprise_rag"]
      interval: 5s
      timeout: 5s
      retries: 10

volumes:
  postgres_data:
```

这是教学环境基线。若 `5432` 已占用，只调整主机侧端口并同步记录，不改变容器内端口。

4. 验证配置与服务：

```powershell
docker compose config --quiet
docker compose up -d db
docker compose ps
```

等待 `db` 变为 `healthy`，再检查 PostgreSQL 和 vector 扩展是否可用：

```powershell
docker compose exec db `
    psql -U rag_user -d enterprise_rag `
    -c "SELECT version();"

docker compose exec db `
    psql -U rag_user -d enterprise_rag `
    -c "SELECT name, default_version FROM pg_available_extensions WHERE name = 'vector';"
```

第二条查询应返回 `vector`。它说明扩展可安装，不代表业务表已经创建。重启数据库服务后再检查健康状态：

```powershell
docker compose restart db
docker compose ps
```

学习结束时可使用 `docker compose stop db` 停止服务；不要删除命名卷。

5. 完成本周总体验收：

```powershell
python .\scripts\validate_manufacturing_dataset.py
git status --short
git diff --check
```

人工抽查 5 份资料，并从 30 道题中选 10 道，在现有资料中定位证据。检查 Git 状态时，只处理本周明确创建或修改的文件，不清理其他已有改动。

### 验证方法

今天成功必须同时满足：

- `docker compose config --quiet` 无错误；
- `docker compose ps` 显示数据库健康；
- PostgreSQL 查询能返回版本信息；
- 可用扩展查询能返回 `vector`；
- 数据验证脚本以零错误结束；
- 抽查 5 份文档能说明设备、版本、状态和来源；
- 至少 10 道题能在资料中定位依据；
- 仓库中没有第三方原始手册、真实敏感信息或 `.env`。

### 当天可见产出

- `compose.yaml` 与 `.env.example`；
- 一个健康的 PostgreSQL + pgvector 本地环境；
- 数据集验证结果和人工抽查记录；
- 本周复盘与下一周明确输入。

### 与下周的衔接

Week 2 将把 `documents.csv` 中的文档身份与版本关系转成数据库模型，把 Markdown 文档解析成带来源元数据的 Chunk，并用 PostgreSQL + pgvector 代替当前全局内存索引。本周没有通过的数据或版本规则，不能直接带入数据库。

### 视频素材与 Git

整理一条 6～10 分钟周总结的提纲：

```text
1. 旧 Mini RAG 为什么不知道文档版本
2. 为什么先把范围缩到三类设备
3. 元数据、来源登记和 synthetic/demo 各解决什么问题
4. 展示 v1.0 inactive 与 v1.1 active
5. 展示 20 条工单、30 道题和验证脚本
6. 展示 pgvector 容器健康状态
7. 一个真实踩坑或仍未解决的问题
```

录屏前隐藏本地用户路径、账户、`.env` 和任何 Token。最终检查后只暂存 Compose 与公开示例配置：

```powershell
git diff -- .\compose.yaml .\.env.example
git diff --check
git add -- .\compose.yaml .\.env.example
git diff --cached
git commit -m "chore: add local pgvector compose environment"
```

### 当天完成清单

- [ ] 我能解释 PostgreSQL、pgvector、Compose 和命名卷各自的职责。
- [ ] Compose 配置通过检查，数据库达到健康状态。
- [ ] 查询确认 `vector` 扩展可用，没有虚构迁移或持久化结果。
- [ ] 数据验证脚本与人工抽查都通过。
- [ ] 我完成了周复盘并留下可用的视频素材。

# Week 1 完成标准

- [ ] 我能用自己的话讲清本周为什么先做可信数据，而不是直接替换向量库。
- [ ] 项目范围只有三类设备、六台资产和 30 道题，没有两套口径。
- [ ] 15 份资料版本都有稳定 ID、版本、状态、来源和 `synthetic/demo` 标识。
- [ ] 空压机与输送机各有一组可解释的 v1.0 旧版和 v1.1 当前版。
- [ ] 20 条工单只使用合法设备 ID，日期、引用版本、故障与安全步骤相互一致。
- [ ] 30 道固定题覆盖 8/6/6/4/3/3 六类结构，至少 10 道已有明确证据。
- [ ] `scripts/validate_manufacturing_dataset.py` 能重复运行并以零错误结束。
- [ ] 任意抽查 5 份资料，都能说明设备类型、版本、状态、来源和安全边界。
- [ ] PostgreSQL + pgvector 环境能够健康启动并查询到 `vector` 扩展。
- [ ] 我保留了周总结素材，检查了 Git 差异，并且没有提交 `.env`、真实数据或未经许可的第三方原件。

本周实际完成：

本周最重要的理解：

仍然模糊的概念：

遇到的卡点：

测试/评测结果：

与原计划的偏差：

视频素材：

Git commits：

下周开始前必须解决：
