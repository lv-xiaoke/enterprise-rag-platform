# Day 9：制作可公开、可重建的企业制度演示数据

今天将直接制作并冻结 4 份虚构企业制度 PDF，使项目获得可公开复现的多文档演示语料，并为面试中的评测数据设计、来源追溯与敏感数据边界问题提供可核对依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：4 份带文字层、固定两页、可由 YAML 重建并由 SHA-256 清单冻结的虚构企业制度 PDF  
> 当前真实状态：已完成  
> 对应总体安排：Day 9

## 一、今天完成后的项目变化

### 升级前

```text
现有 data/evaluation 只服务于旧 FAISS 单 PDF 基线
→ data/documents/ 被 Git 忽略，PDF 需要使用者自行准备
→ 仓库没有可公开提交的多文档企业制度语料
→ 没有固定页码事实、跨文档场景、无答案空间和文件完整性清单
```

### 升级后

```text
data/demo_policies/policies.yaml（唯一事实源）
→ scripts/generate_demo_pdfs.py（生成 + 文字层/页码/敏感模式校验）
→ 4 份固定两页的文本型 PDF
→ data/demo_policies/manifest.json（版本、页数、字符数、SHA-256）
→ 可上传到同一知识库，供 Day 10 固定问题集与 Day 11 参数实验复用
```

### 今天在完整项目中的位置

- 所属阶段：可靠性与数据。
- 所属链路：为文档入库、pgvector 检索、数据库版 RAG、来源追溯和拒答提供固定输入。
- 今天的输入：Day 8 已稳定的上传失败处理、现有文本型 PDF 解析能力、`chunk_size=200`、`overlap=40` 和数据库版多文档 API。
- 今天的输出：4 份虚构制度 PDF、可重复生成脚本、语料说明和完整性清单。
- 下一天为什么需要它：Day 10 必须针对一个不再随意变化的语料版本标注问题、预期页码证据和拒答标签。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `app/services/pdf_service.py` 使用 `pypdf==6.15.0` 按物理页提取文本，并在整份 PDF 无文字层时明确失败。
- `[当前事实]` `app/services/document_ingestion_service.py` 按页使用 `chunk_size=200`、`overlap=40` 切块，保存页码、Chunk 顺序和 512 维向量。
- `[当前事实]` `POST /knowledge-bases/{knowledge_base_id}/documents` 可以把多份 PDF 上传到指定知识库，成功响应包含动态页数和 Chunk 数。
- `[当前事实]` Day 1～Day 8 都有用户完成标记及匹配提交；当前最新提交为 `a23ce16 Day8`。
- `[当前事实]` 当前 `git status --short` 无输出，生成本计划前工作区干净。

### 仍然缺少

- `[当前事实]` 仓库中没有 `data/demo_policies/`，也没有 3～5 份可公开提交的企业制度 PDF。
- `[当前事实]` `data/documents/` 被 `.gitignore` 忽略，不能承担可复现演示语料的职责。
- `[当前事实]` 现有 `data/evaluation/` 是旧 FAISS 单 PDF 基线，不能证明新架构的多文档检索、跨文档来源或拒答能力。
- `[当前事实]` 当前依赖没有 PDF 生成工具；今天使用独立的 `requirements-demo.txt` 固定 `reportlab==5.0.1`，避免把演示数据生成依赖混入 API 运行依赖。
- `[当前事实]` 当前没有语料版本、预期页码标记、敏感模式扫描和 PDF 哈希清单。

### 待实测

- `[待实测]` 当前 Windows 环境是否存在微软雅黑、黑体或宋体等可嵌入中文字体；脚本会逐个检查，并允许通过 `--font-path` 指定字体。
- `[待实测]` ReportLab 生成的 4 份 PDF 是否都恰好为两页，且 `pypdf` 能按页提取所有预期事实标记。
- `[待实测]` 4 份 PDF 实际入库后的 Chunk 数；页数应固定为 2，Chunk 数取决于提取文本长度，是动态值。
- `[待实测]` PDF 的人工视觉检查结果；程序可验证文字层和页码事实，但仍需任选两页确认没有溢出、乱码或遮挡。

### 需要保护的用户修改

- 生成本计划时工作区干净；仍只按当天明确文件清单操作，不处理未来出现的其他修改，不恢复文件，也不使用 `git add .`。

## 三、今天必须理解的核心知识

### 1. 合成演示数据与真实敏感数据边界

- 一句话解释：演示语料应具有真实业务结构，但组织、人员、流程和数值必须是为演示虚构的，不从真实公司制度复制。
- 在当前项目中的职责：让 PDF 可以提交到公开仓库、录制演示并反复用于检索，而不暴露内部资料或个人信息。
- 与其他组件的关系：YAML 是内容事实源，生成脚本会在写 PDF 前扫描邮箱、手机号、身份证号、银行卡号、疑似 API Key 和数据库连接串。
- 容易混淆的点：写上“仅供演示”不能自动消除真实资料的敏感性；内容本身必须从源头虚构。
- 面试一句话：我使用结构化合成制度语料覆盖真实 RAG 场景，同时用模式扫描和人工复核控制公开数据边界。

### 2. 可重建数据与冻结版本

- 一句话解释：可重建表示 PDF 能从受版本控制的源文件重新生成；冻结表示进入评测后，源内容和输出哈希不能被临时改动。
- 在当前项目中的职责：`policies.yaml` 固定语义内容，`generate_demo_pdfs.py` 固定版式，`manifest.json` 固定每个 PDF 的 SHA-256、页数和文字层字符数。
- 与其他组件的关系：Day 10 的问题和预期证据引用 `corpus_version=2026-09-04-v1`，Day 11 才能在相同数据上公平比较参数。
- 容易混淆的点：文件名不变不代表数据没变；哈希变化说明 PDF 字节已经变化，必须重新评估问题和证据。
- 面试一句话：我先冻结语料版本再建立评测集，避免根据模型结果反向修改文档造成数据泄漏和指标虚高。

### 3. 页码事实、Chunk 与来源追溯

- 一句话解释：PDF 的物理页码在入库时随 Chunk 保存，回答返回的 `page_number` 才能定位到原文。
- 在当前项目中的职责：每份 PDF 强制两页，每页配置两个预期事实标记，生成后用 `pypdf` 验证标记确实出现在指定物理页。
- 与其他组件的关系：`PDFService` 按页提取，`DocumentIngestionService` 在每页内部切块，`ChunkRepository` 保存 `page_number`，查询接口返回文档名、页码和原文。
- 容易混淆的点：文档正文中打印的“第 2 页”只是可见文字；真正用于来源追溯的是 PDF 页序和数据库 `chunks.page_number`。
- 面试一句话：我在数据生成阶段就固定并验证页码事实，使来源追溯不是回答生成后的补丁。

### 4. 覆盖空间与无答案空间

- 一句话解释：覆盖空间规定系统应该能回答什么，无答案空间明确语料刻意没有什么。
- 在当前项目中的职责：4 份文档覆盖人事、财务、采购和行政，并留下股权激励、海外签证补贴、VPN、客户退款和生产事故等缺失主题。
- 与其他组件的关系：跨文档场景检验多来源整合，无答案主题在 Day 10 才转化为正式拒答用例。
- 容易混淆的点：今天只设计语料覆盖边界，不提前编写 12 道可回答题和 6 道无答案题，也不调阈值。
- 面试一句话：我不仅设计答案，还显式保留无答案空间，用来评估系统是否会在证据不足时拒答。

## 四、升级涉及的文件

| 文件                                        | 操作     | 作用                                    |
| ----------------------------------------- | ------ | ------------------------------------- |
| `requirements-demo.txt`                   | 新建     | 固定仅用于演示 PDF 生成的 ReportLab 版本          |
| `data/demo_policies/policies.yaml`        | 新建     | 保存 4 份虚构制度的唯一事实源、页级标记与覆盖边界            |
| `scripts/generate_demo_pdfs.py`           | 新建     | 生成 PDF，校验源数据、敏感模式、页数、文字层和预期事实，并输出哈希清单 |
| `data/demo_policies/README.md`            | 新建     | 说明语料范围、跨文档场景、无答案空间和冻结规则               |
| `data/demo_policies/pdfs/员工请假与考勤制度.pdf`   | 脚本生成   | 人事领域两页文本型 PDF                         |
| `data/demo_policies/pdfs/差旅与费用报销制度.pdf`   | 脚本生成   | 财务领域两页文本型 PDF                         |
| `data/demo_policies/pdfs/采购与办公资产管理制度.pdf` | 脚本生成   | 采购与资产领域两页文本型 PDF                      |
| `data/demo_policies/pdfs/访客与会议室管理办法.pdf`  | 脚本生成   | 行政领域两页文本型 PDF                         |
| `data/demo_policies/manifest.json`        | 脚本生成   | 冻结语料版本、页数、文字字符数和 SHA-256              |
| `docs/17天每日学习/Day09.md`                   | 已生成，保留 | 今日升级手册与可选执行记录                         |

### 今日不做

- 不建立 12 道可回答题和 6 道无答案题，也不标注正式评测标签；这属于 Day 10。
- 不比较 Top-K、阈值、Recall、MRR、拒答率或延迟；这属于 Day 11。
- 不修改上传、检索、RAG、事务或数据库表结构。
- 不把真实公司制度、合同、姓名、联系方式、账号或内部资料放入演示语料。
- 不根据试问结果临时修改 PDF 来制造更高分数。

## 五、按顺序完成项目升级

### 步骤 1：固定演示 PDF 生成依赖（建议 3 分钟）

**目标**

把数据生成工具的依赖与 API 运行依赖分开，并固定今天核对过的 ReportLab 版本。

**修改位置**

- 文件：`requirements-demo.txt`
- 定位：当天新文件，当前仓库不存在。
- 操作：新建完整文件。

**复制下面的完整代码**

```text
reportlab==5.0.1
```

**这段代码怎样工作**

- 输入：`python -m pip install -r requirements-demo.txt`。
- 输出：安装用于生成文本型 PDF 的 ReportLab；当前固定版本要求 Python 3.9 及以上。
- 调用谁：由 pip 解析并安装，不被 FastAPI 应用导入。
- 被谁调用：`scripts/generate_demo_pdfs.py`。
- 正常路径：安装成功后可以导入 `reportlab.pdfbase` 和 `reportlab.platypus`。
- 失败路径：网络不可用、Python 版本过低或虚拟环境不可写时，pip 返回非零退出码；不影响当前 API 源代码和数据库。

**完成本步骤后的预期状态**

仓库明确区分“运行 RAG API 的依赖”和“重建演示 PDF 的工具依赖”。

### 步骤 2：建立 4 份制度的唯一事实源（建议 15 分钟）

**目标**

用一个可审查的 YAML 文件固定文档内容、物理页结构、页级事实标记、跨文档场景和无答案空间。

**修改位置**

- 文件：`data/demo_policies/policies.yaml`
- 定位：当天新文件；先创建 `data/demo_policies/pdfs/` 目录。
- 操作：新建完整文件。

**复制下面的完整代码**

```yaml
schema_version: 1
corpus_version: "2026-09-04-v1"
organization: "星河协作科技有限公司（虚构）"
fictional_notice: "本文件全部内容均为项目演示而虚构，不代表任何真实组织的制度。"

cross_document_scenarios:
  - "员工因公出差时，需要同时结合考勤登记规则与差旅申请、报销规则。"
  - "采购办公设备后，需要同时结合采购验收、资产登记规则与财务付款凭证规则。"

reserved_absent_topics:
  - "股权激励与股票期权归属"
  - "海外出差签证与境外补贴"
  - "远程接入、VPN 与信息安全授权"
  - "客户合同退款与违约赔偿"
  - "生产事故响应与灾难恢复"

documents:
  - filename: "员工请假与考勤制度.pdf"
    title: "员工请假与考勤制度"
    domain: "人事"
    owner: "人力资源部"
    version: "DEMO-v1.0"
    effective_date: "2026-09-01"
    pages:
      - page_title: "第一章 适用范围与日常考勤"
        expected_markers:
          - "弹性签到窗口为 08:30 至 09:30"
          - "连续三天以上年假须至少提前七个工作日申请"
        sections:
          - heading: "一、适用范围"
            paragraphs:
              - "本制度适用于星河协作科技有限公司（虚构）的全体正式员工、试用期员工和经部门确认纳入统一考勤的项目人员。外包服务商按照双方虚构项目约定管理，不在本制度范围内。"
              - "本制度只用于企业 RAG 项目演示。所有部门、流程、期限和金额均为合成内容，不对应任何真实组织或个人。"
          - heading: "二、工作时间与签到"
            paragraphs:
              - "标准工作日为周一至周五，每日工作时间为 09:00 至 18:00，午间休息时间为 12:00 至 13:00。弹性签到窗口为 08:30 至 09:30，员工应在完成签到后保证当日工作时长。"
              - "超过 09:30 且没有已批准请假、出差或外勤记录的，记为迟到。单月累计三次迟到时，直属负责人应与员工完成一次考勤提醒并记录改进措施。"
          - heading: "三、年假申请"
            paragraphs:
              - "一天以内的年假应至少提前三个工作日在系统提交；连续三天以上年假须至少提前七个工作日申请。申请先由直属负责人确认工作交接，再由人力资源部核对可用假期。"
              - "紧急情况无法提前申请时，员工应在当日上班后两小时内通知直属负责人，并在恢复工作后的一个工作日内补交申请。补交只完善记录，不自动改变审批结果。"
      - page_title: "第二章 病假、出差与异常处理"
        expected_markers:
          - "病假超过一个工作日须提交医疗机构证明"
          - "审批完成的出差日期按正常出勤登记"
        sections:
          - heading: "四、病假与材料"
            paragraphs:
              - "病假可以先通过系统提交说明。病假超过一个工作日须提交医疗机构证明，证明应在返岗后的两个工作日内补充；员工不得在演示系统中上传包含真实身份信息的材料。"
              - "人力资源部只核对请假日期、证明类型和审批状态。本演示制度不记录诊断详情，也不要求在公开演示数据中填写姓名、证件号码或联系方式。"
          - heading: "五、出差期间的考勤"
            paragraphs:
              - "员工应在出发前完成差旅申请。审批完成的出差日期按正常出勤登记，出差期间无需重复提交外勤签到，但每日工作安排仍由直属负责人确认。"
              - "出差交通、住宿、餐费标准和返程后的报销期限不在本文件定义，统一以《差旅与费用报销制度》为准。未完成差旅审批的行程不能仅凭考勤记录获得费用报销。"
          - heading: "六、异常更正"
            paragraphs:
              - "漏签员工应在两个工作日内提交更正，说明日期、时段和原因，由直属负责人确认。每月最后一个工作日之后提交的更正进入下一考勤周期复核。"
              - "考勤系统不可用时，人力资源部发布统一通知并保留替代记录；员工不应通过共享账号、代签或伪造截图完成考勤。"

  - filename: "差旅与费用报销制度.pdf"
    title: "差旅与费用报销制度"
    domain: "财务"
    owner: "财务部"
    version: "DEMO-v1.0"
    effective_date: "2026-09-01"
    pages:
      - page_title: "第一章 差旅申请与费用标准"
        expected_markers:
          - "一线城市住宿上限为每晚六百元"
          - "其他城市住宿上限为每晚四百五十元"
        sections:
          - heading: "一、出发前申请"
            paragraphs:
              - "员工因公出差应在出发前提交差旅申请，写明目的、地点、起止日期、预计费用和工作交付。直属负责人批准业务必要性后，由财务部检查预算科目。"
              - "未经批准自行发生的费用原则上不予报销。紧急出差应在出发前取得直属负责人书面确认，并在返程后两个工作日内补齐系统申请。"
          - heading: "二、住宿与交通标准"
            paragraphs:
              - "境内差旅按城市类别控制住宿预算：一线城市住宿上限为每晚六百元，其他城市住宿上限为每晚四百五十元。金额均为虚构的含税上限，不代表任何真实企业标准。"
              - "员工优先选择公共交通和经济合理的出行方案。市内交通补助上限为每日八十元，超出部分需要在费用发生前取得部门负责人的补充批准。"
          - heading: "三、餐费与超标处理"
            paragraphs:
              - "出差餐费补助上限为每日一百元，由出差起止日期按自然日计算。由会议主办方统一提供餐食的时段，不重复申领餐费补助。"
              - "确因展会、临时改签或目的地供应紧张导致住宿超标的，员工应保存原因说明，并由部门负责人和财务负责人共同审批。"
      - page_title: "第二章 报销、复核与采购付款衔接"
        expected_markers:
          - "返程后十个工作日内提交报销"
          - "财务复核在五个工作日内完成"
        sections:
          - heading: "四、报销材料与期限"
            paragraphs:
              - "员工应在返程后十个工作日内提交报销，材料包括已批准的差旅申请、费用明细和合法有效的发票。电子发票应避免重复报销，并保留可核验的原始文件。"
              - "缺少必要凭证时，员工应提交情况说明并取得部门负责人确认；情况说明不能替代税务规定要求的票据，也不能用于报销个人消费。"
          - heading: "五、复核与支付"
            paragraphs:
              - "财务复核在五个工作日内完成，重点检查预算、审批链、费用类别、发票和重复提交情况。材料被退回后，复核时限从补齐材料之日重新计算。"
              - "通过复核的报销在三个工作日内进入付款流程。演示数据只描述流程节点，不包含银行账户、收款人身份或任何真实支付信息。"
          - heading: "六、采购付款凭证"
            paragraphs:
              - "办公设备采购付款应同时附采购审批记录、供应商报价或比价记录、到货验收记录和合法发票。缺少验收记录时，财务部暂不发起付款。"
              - "采购金额分级、报价数量和固定资产登记规则由《采购与办公资产管理制度》定义；财务部不以付款审核替代采购审批和资产验收。"

  - filename: "采购与办公资产管理制度.pdf"
    title: "采购与办公资产管理制度"
    domain: "采购与行政"
    owner: "采购组与行政部"
    version: "DEMO-v1.0"
    effective_date: "2026-09-01"
    pages:
      - page_title: "第一章 采购申请与分级审批"
        expected_markers:
          - "一千元以内由申请人直属负责人审批"
          - "单次采购金额超过五千元须取得三家供应商报价"
        sections:
          - heading: "一、采购前提"
            paragraphs:
              - "办公用品、设备和通用服务采购应先确认业务用途、数量、预算科目和期望到货日期。申请人不得拆分订单规避审批级别，也不得先收货后补普通采购申请。"
              - "本制度中的金额、供应商和流程均为虚构演示内容。公开数据中不保存真实供应商名称、联系人、报价文件或合同编号。"
          - heading: "二、金额分级"
            paragraphs:
              - "单次采购金额一千元以内由申请人直属负责人审批；超过一千元且不超过五千元的采购，需要至少两家供应商报价并由部门负责人批准。"
              - "单次采购金额超过五千元须取得三家供应商报价，并由部门负责人和财务负责人共同确认预算。无法取得足够报价时，应书面说明唯一来源或紧急原因。"
          - heading: "三、紧急采购"
            paragraphs:
              - "影响办公连续性的紧急采购可以先取得部门负责人和行政负责人的书面确认，随后在两个工作日内补齐申请、报价和用途说明。"
              - "价格优惠、口头承诺或个人垫付不构成跳过审批的理由。涉及长期服务的采购仍需明确服务范围、验收方式和终止条件。"
      - page_title: "第二章 到货验收、资产登记与付款"
        expected_markers:
          - "到货后两个工作日内完成验收"
          - "固定资产由行政部门登记资产编号"
        sections:
          - heading: "四、到货验收"
            paragraphs:
              - "申请人和资产管理员应在到货后两个工作日内完成验收，核对品名、数量、规格、外观和基础功能。发现不符时应暂停领用并联系采购组处理。"
              - "验收记录应注明采购申请、到货日期、验收结论和异常说明。没有通过验收的设备不得标记为可领用，也不得作为财务付款完成的依据。"
          - heading: "五、资产登记与领用"
            paragraphs:
              - "达到固定资产登记标准的设备，由行政部门登记资产编号、所属部门、保管角色和领用日期。公开演示数据只使用角色，不记录真实员工姓名。"
              - "设备调拨、归还和报废都应更新资产状态。普通低值耗材按部门汇总登记，不为每件耗材生成独立资产编号。"
          - heading: "六、付款衔接"
            paragraphs:
              - "采购组在验收通过后汇总审批记录、报价记录、验收记录和发票，交财务部进行付款复核。付款时限和凭证合法性要求以《差旅与费用报销制度》的采购付款条款为准。"
              - "申请人、验收人和付款复核人承担不同职责；任何单一角色都不能独立完成从申请到付款的全部环节。"

  - filename: "访客与会议室管理办法.pdf"
    title: "访客与会议室管理办法"
    domain: "行政"
    owner: "行政部"
    version: "DEMO-v1.0"
    effective_date: "2026-09-01"
    pages:
      - page_title: "第一章 访客预约与现场管理"
        expected_markers:
          - "外部访客须至少提前一个工作日登记"
          - "访客证当日十八点三十分自动失效"
        sections:
          - heading: "一、预约登记"
            paragraphs:
              - "因会议、交付或面试进入办公区的外部访客须至少提前一个工作日登记，由接待部门填写来访单位类别、来访目的、预计时间、人数和接待角色。"
              - "公开演示数据不填写真实姓名、证件号码、手机号码或车牌。现场演示只展示虚构角色和流程状态。"
          - heading: "二、签到与陪同"
            paragraphs:
              - "访客到达后由前台核对预约状态，发放当日访客证，并通知接待角色到场。未预约访客需由接待部门负责人确认后才能进入会议区域。"
              - "访客在办公区内应由接待人员陪同，不得进入标记为受限的机房、档案区或设备区，也不得拍摄屏幕、白板或未公开文件。"
          - heading: "三、离场与访客证"
            paragraphs:
              - "访客离场时应归还访客证，由前台完成离场状态登记。访客证当日十八点三十分自动失效，跨日访问必须重新提交预约。"
              - "遗失访客证时，接待人员应立即通知前台停用该证，并陪同访客完成离场；本演示流程不记录任何真实证件信息。"
      - page_title: "第二章 会议室预订与使用"
        expected_markers:
          - "会议开始前两小时取消预订"
          - "接待外部访客时须同时完成访客登记和会议室预订"
        sections:
          - heading: "四、预订规则"
            paragraphs:
              - "会议组织者应选择满足人数和设备需求的会议室，填写主题、开始时间、结束时间和组织角色。同一组织者不得为同一时段重复占用多个会议室。"
              - "计划取消或改为线上会议时，应在会议开始前两小时取消预订。连续两次未使用且未取消的，行政部可以暂停该组织者一周的提前预订权限。"
          - heading: "五、外部访客会议"
            paragraphs:
              - "接待外部访客时须同时完成访客登记和会议室预订，会议室预订本身不能替代访客预约。接待角色负责在预约时间到前台迎接。"
              - "含未公开资料的会议结束后，组织者应带走纸质材料并清理白板。公开演示不得展示任何真实客户名称、项目代号或合同内容。"
          - heading: "六、使用结束"
            paragraphs:
              - "使用者应按预订结束时间离场，关闭显示设备并恢复桌椅。发现设备故障时，在会议室状态中提交故障类型，由行政部安排处理。"
              - "会议室容量、访客人数和设备需求不匹配时，应更换会议室，不得通过取消访客登记来绕过现场管理要求。"
```

**这段代码怎样工作**

- 输入：4 份制度的标题、领域、版本、固定页面、章节段落和页级预期标记。
- 输出：生成脚本可消费的结构化语料定义。
- 调用谁：不直接调用应用代码；由 `yaml.safe_load()` 读取。
- 被谁调用：`scripts/generate_demo_pdfs.py`。
- 正常路径：4 个唯一 `.pdf` 文件名、4 个领域、每份 2 页且每页至少 2 个标记，满足脚本校验。
- 失败路径：文档数量越界、文件名重复、页为空、标记不在对应页或检测到敏感模式时，生成器在创建输出目录前终止。

**完成本步骤后的预期状态**

语料内容可以像代码一样审查，PDF 不再是无法追踪来源的手工二进制文件。

### 步骤 3：实现确定性的 PDF 生成与校验脚本（建议 18 分钟）

**目标**

从 YAML 生成 4 份中文文本型 PDF，并自动检查敏感模式、物理页数、按页文字层、预期事实和 SHA-256 清单。

**修改位置**

- 文件：`scripts/generate_demo_pdfs.py`
- 定位：当天新文件，当前 `scripts/` 只有旧评测脚本。
- 操作：新建完整文件。

**复制下面的完整代码**

```python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html import escape
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = PROJECT_ROOT / "data" / "demo_policies" / "policies.yaml"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "demo_policies" / "pdfs"
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "demo_policies" / "manifest.json"
FONT_NAME = "DemoPolicyCJK"
FONT_CANDIDATES = (
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
)
SENSITIVE_PATTERNS = {
    "电子邮箱": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.IGNORECASE,
    ),
    "中国大陆手机号": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "中国大陆身份证号": re.compile(
        r"(?<!\d)\d{17}[0-9Xx](?!\d)"
    ),
    "疑似银行卡号": re.compile(r"(?<!\d)\d{16,19}(?!\d)"),
    "疑似 API Key": re.compile(
        r"(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16})"
    ),
    "数据库连接串": re.compile(
        r"(?:postgresql|postgres)://[^\s]+",
        re.IGNORECASE,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="生成并验证 Day 9 虚构企业制度 PDF。"
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="YAML 事实源路径。",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="PDF 输出目录。",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="完整性清单路径。",
    )
    parser.add_argument(
        "--font-path",
        type=Path,
        default=None,
        help="可选的中文 TrueType/OpenType 字体路径。",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="不重新生成，只验证已有 PDF 和清单。",
    )
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 必须是非空字符串")
    return value.strip()


def scan_sensitive_data(text: str) -> None:
    for label, pattern in SENSITIVE_PATTERNS.items():
        if pattern.search(text):
            raise ValueError(
                f"演示数据疑似包含{label}；请改为不可联系的虚构描述"
            )


def page_source_text(page: dict[str, Any]) -> str:
    parts = [require_non_empty_string(page.get("page_title"), "page_title")]
    sections = page.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("每一页都必须包含至少一个 section")

    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("section 必须是对象")
        parts.append(
            require_non_empty_string(section.get("heading"), "heading")
        )
        paragraphs = section.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            raise ValueError("每个 section 都必须包含 paragraphs")
        parts.extend(
            require_non_empty_string(paragraph, "paragraph")
            for paragraph in paragraphs
        )

    return "\n".join(parts)


def validate_source(payload: Any, raw_source: str) -> dict[str, Any]:
    scan_sensitive_data(raw_source)
    if not isinstance(payload, dict):
        raise ValueError("YAML 根节点必须是对象")
    if payload.get("schema_version") != 1:
        raise ValueError("schema_version 必须为 1")

    require_non_empty_string(payload.get("corpus_version"), "corpus_version")
    require_non_empty_string(payload.get("organization"), "organization")
    require_non_empty_string(
        payload.get("fictional_notice"),
        "fictional_notice",
    )

    scenarios = payload.get("cross_document_scenarios")
    if not isinstance(scenarios, list) or len(scenarios) < 2:
        raise ValueError("至少需要两个跨文档场景")
    for scenario in scenarios:
        require_non_empty_string(scenario, "cross_document_scenario")

    absent_topics = payload.get("reserved_absent_topics")
    if not isinstance(absent_topics, list) or len(absent_topics) < 3:
        raise ValueError("至少需要三个明确的无答案主题")
    for topic in absent_topics:
        require_non_empty_string(topic, "reserved_absent_topic")

    documents = payload.get("documents")
    if not isinstance(documents, list) or not 3 <= len(documents) <= 5:
        raise ValueError("documents 数量必须在 3 到 5 之间")

    filenames: set[str] = set()
    domains: set[str] = set()
    for document_index, document in enumerate(documents, start=1):
        if not isinstance(document, dict):
            raise ValueError(f"第 {document_index} 个 document 必须是对象")

        filename = require_non_empty_string(
            document.get("filename"),
            f"documents[{document_index}].filename",
        )
        if Path(filename).name != filename or not filename.lower().endswith(
            ".pdf"
        ):
            raise ValueError(f"非法 PDF 文件名：{filename}")
        if filename in filenames:
            raise ValueError(f"PDF 文件名重复：{filename}")
        filenames.add(filename)

        require_non_empty_string(document.get("title"), "title")
        domain = require_non_empty_string(document.get("domain"), "domain")
        domains.add(domain)
        require_non_empty_string(document.get("owner"), "owner")
        require_non_empty_string(document.get("version"), "version")
        require_non_empty_string(
            document.get("effective_date"),
            "effective_date",
        )

        pages = document.get("pages")
        if not isinstance(pages, list) or len(pages) != 2:
            raise ValueError(f"{filename} 必须恰好定义两页")

        for page_number, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                raise ValueError(f"{filename} 第 {page_number} 页必须是对象")
            source_text = normalize_text(page_source_text(page))
            markers = page.get("expected_markers")
            if not isinstance(markers, list) or len(markers) < 2:
                raise ValueError(
                    f"{filename} 第 {page_number} 页至少需要两个标记"
                )
            for marker in markers:
                marker_text = require_non_empty_string(
                    marker,
                    "expected_marker",
                )
                if normalize_text(marker_text) not in source_text:
                    raise ValueError(
                        f"{filename} 第 {page_number} 页的标记不在正文中"
                    )

    if len(domains) < 2:
        raise ValueError("演示语料至少覆盖两个业务领域")

    return payload


def resolve_font(explicit_font: Path | None) -> Path:
    candidates = (
        (explicit_font,) if explicit_font is not None else FONT_CANDIDATES
    )
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "未找到可嵌入的中文字体；请使用 --font-path 指定 .ttf 或 .ttc 文件"
    )


def register_font(font_path: Path) -> None:
    if FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return
    pdfmetrics.registerFont(
        TTFont(
            FONT_NAME,
            str(font_path),
            subfontIndex=0,
        )
    )


def build_styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            name="PolicyTitle",
            fontName=FONT_NAME,
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17324D"),
            spaceAfter=8 * mm,
            wordWrap="CJK",
        ),
        "meta": ParagraphStyle(
            name="PolicyMeta",
            fontName=FONT_NAME,
            fontSize=9,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#52616B"),
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
        "page_heading": ParagraphStyle(
            name="PageHeading",
            fontName=FONT_NAME,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#1F5A75"),
            spaceBefore=3 * mm,
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
        "section_heading": ParagraphStyle(
            name="SectionHeading",
            fontName=FONT_NAME,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#234E52"),
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
            wordWrap="CJK",
        ),
        "body": ParagraphStyle(
            name="PolicyBody",
            fontName=FONT_NAME,
            fontSize=10.5,
            leading=18,
            firstLineIndent=2 * 10.5,
            textColor=colors.HexColor("#1F2933"),
            spaceAfter=2.5 * mm,
            wordWrap="CJK",
        ),
        "notice": ParagraphStyle(
            name="PolicyNotice",
            fontName=FONT_NAME,
            fontSize=9,
            leading=15,
            textColor=colors.HexColor("#8A3B12"),
            backColor=colors.HexColor("#FFF4E5"),
            borderColor=colors.HexColor("#F2C078"),
            borderWidth=0.5,
            borderPadding=6,
            spaceAfter=5 * mm,
            wordWrap="CJK",
        ),
    }


def make_page_callback(
    title: str,
    organization: str,
    notice: str,
):
    def draw_page(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setTitle(title)
        canvas.setAuthor(organization)
        canvas.setSubject(notice)
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(
            18 * mm,
            12 * mm,
            f"{organization}｜公开演示虚构资料",
        )
        canvas.drawRightString(
            A4[0] - 18 * mm,
            12 * mm,
            f"第 {document.page} 页",
        )
        canvas.restoreState()

    return draw_page


def build_pdf(
    document_data: dict[str, Any],
    organization: str,
    notice: str,
    output_path: Path,
) -> None:
    styles = build_styles()
    pdf_document = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=document_data["title"],
        author=organization,
        subject=notice,
        pageCompression=1,
        invariant=1,
    )

    story: list[Any] = []
    for page_index, page in enumerate(document_data["pages"]):
        if page_index > 0:
            story.append(PageBreak())
        else:
            story.append(
                Paragraph(
                    escape(document_data["title"]),
                    styles["title"],
                )
            )
            metadata = (
                f"{escape(organization)}｜{escape(document_data['owner'])}｜"
                f"版本 {escape(document_data['version'])}｜"
                f"生效日期 {escape(document_data['effective_date'])}"
            )
            story.append(Paragraph(metadata, styles["meta"]))
            story.append(
                Paragraph(
                    escape(notice),
                    styles["notice"],
                )
            )

        story.append(
            Paragraph(
                escape(page["page_title"]),
                styles["page_heading"],
            )
        )
        for section in page["sections"]:
            story.append(
                Paragraph(
                    escape(section["heading"]),
                    styles["section_heading"],
                )
            )
            for paragraph in section["paragraphs"]:
                story.append(
                    Paragraph(
                        escape(paragraph),
                        styles["body"],
                    )
                )
            story.append(Spacer(1, 1.5 * mm))

    callback = make_page_callback(
        title=document_data["title"],
        organization=organization,
        notice=notice,
    )
    pdf_document.build(
        story,
        onFirstPage=callback,
        onLaterPages=callback,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_pdf(
    document_data: dict[str, Any],
    pdf_path: Path,
) -> dict[str, Any]:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"缺少演示 PDF：{pdf_path}")

    reader = PdfReader(pdf_path)
    expected_pages = document_data["pages"]
    if len(reader.pages) != len(expected_pages):
        raise ValueError(
            f"{pdf_path.name} 页数应为 {len(expected_pages)}，"
            f"实际为 {len(reader.pages)}"
        )

    page_text_characters: list[int] = []
    for page_number, (pdf_page, page_data) in enumerate(
        zip(reader.pages, expected_pages),
        start=1,
    ):
        extracted_text = pdf_page.extract_text() or ""
        normalized_page = normalize_text(extracted_text)
        if not normalized_page:
            raise ValueError(
                f"{pdf_path.name} 第 {page_number} 页没有可提取文字"
            )
        scan_sensitive_data(extracted_text)
        for marker in page_data["expected_markers"]:
            if normalize_text(marker) not in normalized_page:
                raise ValueError(
                    f"{pdf_path.name} 第 {page_number} 页缺少预期事实标记"
                )
        page_text_characters.append(len(normalized_page))

    return {
        "filename": pdf_path.name,
        "title": document_data["title"],
        "domain": document_data["domain"],
        "sha256": sha256_file(pdf_path),
        "page_count": len(reader.pages),
        "page_text_characters": page_text_characters,
        "expected_markers": [
            page["expected_markers"] for page in expected_pages
        ],
    }


def build_manifest(
    payload: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    document_results = [
        inspect_pdf(
            document_data=document_data,
            pdf_path=output_dir / document_data["filename"],
        )
        for document_data in payload["documents"]
    ]
    return {
        "schema_version": 1,
        "corpus_version": payload["corpus_version"],
        "organization": payload["organization"],
        "fictional_notice": payload["fictional_notice"],
        "document_count": len(document_results),
        "cross_document_scenarios": payload[
            "cross_document_scenarios"
        ],
        "reserved_absent_topics": payload["reserved_absent_topics"],
        "documents": document_results,
    }


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def verify_frozen_manifest(
    actual_manifest: dict[str, Any],
    manifest_path: Path,
) -> None:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"缺少冻结清单：{manifest_path}")
    expected_manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    if expected_manifest != actual_manifest:
        raise ValueError(
            "现有 PDF 与 manifest.json 不一致；请确认是否需要升级语料版本"
        )


def main() -> None:
    args = parse_args()
    source_path = args.source.resolve()
    output_dir = args.output_dir.resolve()
    manifest_path = args.manifest.resolve()

    if not source_path.is_file():
        raise FileNotFoundError(f"找不到 YAML 事实源：{source_path}")
    raw_source = source_path.read_text(encoding="utf-8")
    payload = validate_source(
        yaml.safe_load(raw_source),
        raw_source,
    )

    if not args.verify_only:
        font_path = resolve_font(args.font_path)
        register_font(font_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        for document_data in payload["documents"]:
            build_pdf(
                document_data=document_data,
                organization=payload["organization"],
                notice=payload["fictional_notice"],
                output_path=output_dir / document_data["filename"],
            )
        print(f"使用字体：{font_path}")

    actual_manifest = build_manifest(payload, output_dir)
    if args.verify_only:
        verify_frozen_manifest(actual_manifest, manifest_path)
    else:
        write_manifest(actual_manifest, manifest_path)

    for document in actual_manifest["documents"]:
        print(
            "OK："
            f"{document['filename']}，"
            f"{document['page_count']} 页，"
            f"每页文字数 {document['page_text_characters']}"
        )
    print(f"语料版本：{actual_manifest['corpus_version']}")
    print(f"完整性清单：{manifest_path}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR：{exc}", file=sys.stderr)
        raise SystemExit(1) from None
```

**这段代码怎样工作**

- 输入：`policies.yaml`、可选中文字体路径和命令行模式。
- 输出：4 份 PDF 与 `manifest.json`；`--verify-only` 模式不写文件，只对现有结果重新计算并比较。
- 调用谁：ReportLab 负责版式与文字层，`pypdf` 按物理页回读，`hashlib` 计算 SHA-256。
- 被谁调用：开发者在项目根目录手动执行；FastAPI 不在导入链路中。
- 正常路径：源数据通过校验，生成 PDF 后每页能提取文字、命中页级标记，清单写入成功，进程退出码为 0。
- 失败路径：敏感模式、结构错误、中文字体缺失、PDF 页数漂移、文字层缺失、标记错页或清单不一致都会返回退出码 1；错误只说明类别，不回显匹配到的敏感值。

**完成本步骤后的预期状态**

演示 PDF 不依赖手工排版，任何内容变化都可以通过 YAML diff 和清单变化追踪。

### 步骤 4：记录语料边界和冻结规则（建议 7 分钟）

**目标**

让后续使用者明确这批文件是什么、覆盖什么、不覆盖什么，以及何时必须升级语料版本。

**修改位置**

- 文件：`data/demo_policies/README.md`
- 定位：当天新文件。
- 操作：新建完整文件。

**复制下面的完整代码**

```markdown
# 企业制度演示语料

本目录中的组织、制度、部门、流程、期限和金额全部为项目演示而虚构，不对应任何真实组织或个人，也不得混入真实内部资料。

## 当前冻结版本

- 语料版本：`2026-09-04-v1`
- 唯一事实源：`policies.yaml`
- 生成脚本：`../../scripts/generate_demo_pdfs.py`
- 完整性清单：`manifest.json`
- 输出目录：`pdfs/`

## 文件与覆盖范围

| PDF | 领域 | 固定页数 | 主要覆盖 |
| --- | --- | ---: | --- |
| `员工请假与考勤制度.pdf` | 人事 | 2 | 工作时间、年假、病假、出差考勤、异常更正 |
| `差旅与费用报销制度.pdf` | 财务 | 2 | 差旅审批、住宿标准、报销期限、复核、采购付款凭证 |
| `采购与办公资产管理制度.pdf` | 采购与行政 | 2 | 金额分级、报价数量、验收、资产登记、付款衔接 |
| `访客与会议室管理办法.pdf` | 行政 | 2 | 访客预约、陪同、访客证、会议室预订与取消 |

## 跨文档场景

当前语料刻意保留两类需要组合来源的场景，但正式题目和标签留到 Day 10：

1. 员工因公出差时，需要同时结合考勤登记规则与差旅申请、报销规则。
2. 采购办公设备后，需要同时结合采购验收、资产登记规则与财务付款凭证规则。

## 明确保留的无答案空间

当前 4 份 PDF 不定义以下内容，后续可用于拒答评测：

- 股权激励与股票期权归属。
- 海外出差签证与境外补贴。
- 远程接入、VPN 与信息安全授权。
- 客户合同退款与违约赔偿。
- 生产事故响应与灾难恢复。

## 重建和验证

在项目根目录执行：

```powershell
python -m pip install -r requirements-demo.txt
python scripts/generate_demo_pdfs.py
python scripts/generate_demo_pdfs.py --verify-only
```

生成器会检查：

- 文档数量为 3～5 份且至少覆盖两个领域。
- 文件名唯一，每份 PDF 固定两页。
- 每一页存在可提取的文字层和指定事实标记。
- YAML 与 PDF 中不存在常见邮箱、手机号、身份证号、银行卡号、API Key 或数据库连接串模式。
- 当前 PDF 的 SHA-256、页数和文字数与 `manifest.json` 一致。

## 冻结规则

1. 只修改 `policies.yaml`，不要直接编辑生成后的 PDF。
2. 内容变化时先升级 `corpus_version`，再重新生成全部 PDF 和 `manifest.json`。
3. Day 10 建立固定评测集后，不得根据模型回答临时修改文档；确需修改时必须生成新版本并重新核对问题与证据。
4. PDF 可提交到仓库，但不得提交真实公司制度、个人信息、账号、密钥或本地环境配置。


**这段代码怎样工作**

- 输入：今天确定的语料版本、文件清单、覆盖范围和禁止范围。
- 输出：供开发者、评测脚本作者和面试演示者共同遵守的数据契约。
- 调用谁：不调用代码。
- 被谁调用：Day 10～Day 16 的评测、验收、README 和演示工作会引用它。
- 正常路径：使用者按固定命令重建并验证同一版本。
- 失败路径：若哈希变化或页码事实变化，不能继续沿用旧评测标注，必须升级版本并复核。

**完成本步骤后的预期状态**

语料不只是 4 个 PDF 文件，还具备清楚的使用边界和版本治理规则。

### 步骤 5：生成并冻结 4 份 PDF（建议 7 分钟，不含首次安装耗时）

**目标**

实际生成二进制 PDF 和清单，并立即用只读模式复核生成结果。

**修改位置**

- 文件：`data/demo_policies/pdfs/*.pdf` 和 `data/demo_policies/manifest.json`
- 定位：由脚本根据 4 个明确文件名生成；不是手工编辑文件。
- 操作：按第六部分命令安装工具依赖、生成、再次校验并人工打开抽查。

**复制下面的完整代码**

本步骤没有需要手工粘贴的二进制代码；PDF 和 JSON 必须由步骤 3 的完整脚本生成，避免把不可审查的 Base64 或手工二进制内容放进计划。

**这段代码怎样工作**

- 输入：YAML 事实源与本机中文字体。
- 输出：4 份 PDF 和一份 JSON 完整性清单。
- 调用谁：`generate_demo_pdfs.py` 调用 ReportLab、pypdf 和 SHA-256 计算。
- 被谁调用：后续上传 API、Day 10 评测集和 Day 13 多文档持久化验收。
- 正常路径：命令打印 4 行 `OK`、语料版本和清单路径，退出码为 0。
- 失败路径：任何一份 PDF 页数、文字层、页级事实或哈希不一致都会使整体验证失败。

**完成本步骤后的预期状态**

`data/demo_policies/pdfs/` 包含 4 份各 2 页的文本型 PDF，`manifest.json` 可用于判断文件是否被改动。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成、不执行也不回滚 Alembic 迁移；以下只安装独立的数据生成依赖并创建演示文件。所有命令都在项目根目录 `D:\my_develop\A_work_program\AI-study-2609\enterprise-rag-platform` 执行。

### 1. 检查当前状态

目的：确认工作区边界、Python 版本、源文件和本机中文字体候选；先检查再安装。

```powershell
git status --short
python --version
python -m pip show reportlab
Get-Item -LiteralPath 'requirements-demo.txt'
Get-Item -LiteralPath 'data/demo_policies/policies.yaml'
Get-Item -LiteralPath 'scripts/generate_demo_pdfs.py'
Get-ChildItem -LiteralPath 'C:\Windows\Fonts' -File |
    Where-Object { $_.Name -in @('msyh.ttc', 'simhei.ttf', 'simsun.ttc') } |
    Select-Object Name, FullName
```

执行顺序：先看 `git status`，再确认 Python，最后确认当天三个文本文件和字体。  
预期结果：Python 至少为 3.9；`pip show` 在首次安装前可以提示未找到；至少一个字体候选存在。  
失败时检查：虚拟环境是否已激活、文件是否粘贴到正确路径；若没有候选字体，准备一个许可允许嵌入的中文 `.ttf` 或 `.ttc` 路径，生成时通过 `--font-path` 明确指定。

### 2. 执行升级

目的：安装固定工具依赖、生成 PDF、写入清单并用只读模式再次验证。

```powershell
python -m pip install -r requirements-demo.txt
python scripts/generate_demo_pdfs.py
python scripts/generate_demo_pdfs.py --verify-only
Get-ChildItem -LiteralPath 'data/demo_policies/pdfs' -File |
    Select-Object Name, Length
Get-Content -Path 'data/demo_policies/manifest.json' -Raw
```

如果自动检测不到字体，使用已经核对过的明确路径重试，例如：

```powershell
python scripts/generate_demo_pdfs.py `
    --font-path 'C:\Windows\Fonts\msyh.ttc'
python scripts/generate_demo_pdfs.py --verify-only
```

执行顺序：安装 → 生成 → 只读复核 → 查看 4 个文件和清单。  
预期结果：两个脚本命令都以退出码 0 结束；每次打印 4 行 `OK`；清单中 `document_count` 为 4，每份 `page_count` 为 2，SHA-256 为动态的 64 位十六进制字符串。  
失败时检查：先看错误类别；字体问题使用 `--font-path`，页数漂移则减少对应 YAML 页的正文，标记错页则确认标记只出现在指定页面，不要跳过校验。

### 3. 回滚并恢复

今天没有数据库迁移，因此不执行 Alembic downgrade。PDF 属于可再生产物；如源内容确需调整，只修改 `policies.yaml`、升级 `corpus_version`，然后重新运行以下明确命令覆盖 4 个已知输出和清单：

```powershell
python scripts/generate_demo_pdfs.py
python scripts/generate_demo_pdfs.py --verify-only
```

不要删除 `data/demo_policies/`，不要批量删除 PDF，也不要通过清空数据库或删除 Docker Volume 验证今天的任务。

### 预期结果

- `requirements-demo.txt` 只增加 ReportLab 工具依赖，不改变 FastAPI 的运行导入链路。
- 4 份 PDF 都有文字层、恰好 2 个物理页，且每页命中 YAML 中的两个预期标记。
- `manifest.json` 能检测 PDF 内容、字体或版式变化造成的字节差异。
- 尚未运行的安装和生成结果都只是上述预期，不能提前视为已成功。

## 七、验证正常路径

### 启动或准备服务

先完成本地静态校验；这一步不需要数据库或 LLM：

```powershell
python scripts/generate_demo_pdfs.py --verify-only
```

然后启动 PostgreSQL、迁移数据库，并在另一个 PowerShell 窗口启动 API：

```powershell
docker compose up -d postgres
docker compose ps
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

`uvicorn` 是前台进程；保持该窗口运行，在新的项目根目录 PowerShell 窗口执行下面的请求，完成后可在 Uvicorn 窗口按 `Ctrl+C` 退出。

### 执行正常请求或测试

创建一个专用于今天演示语料的知识库。使用 UTF-8 字节发送中文 JSON，返回 ID 是动态值：

```powershell
$day9BaseUrl = 'http://127.0.0.1:8000'
$day9KnowledgeBaseBody = @{
    name = 'Day9 企业制度演示库'
    description = '全部内容均为虚构的公开演示语料'
} | ConvertTo-Json
$day9KnowledgeBase = Invoke-RestMethod `
    -Method Post `
    -Uri "$day9BaseUrl/knowledge-bases" `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($day9KnowledgeBaseBody))
$day9KnowledgeBaseId = $day9KnowledgeBase.id
$day9KnowledgeBase
```

如果此前已经创建同名知识库并收到 HTTP 409，不要删除数据；从列表中读取它的动态 ID：

```powershell
$day9KnowledgeBase = Invoke-RestMethod `
    -Method Get `
    -Uri "$day9BaseUrl/knowledge-bases" |
    Where-Object { $_.name -eq 'Day9 企业制度演示库' } |
    Select-Object -First 1
if ($null -eq $day9KnowledgeBase) {
    throw '未找到 Day9 企业制度演示库'
}
$day9KnowledgeBaseId = $day9KnowledgeBase.id
```

按明确文件清单上传 4 份 PDF；Embedding 首次下载模型的时间不计入 60 分钟核心时间：

```powershell
$day9PdfPaths = @(
    'data/demo_policies/pdfs/员工请假与考勤制度.pdf',
    'data/demo_policies/pdfs/差旅与费用报销制度.pdf',
    'data/demo_policies/pdfs/采购与办公资产管理制度.pdf',
    'data/demo_policies/pdfs/访客与会议室管理办法.pdf'
)

foreach ($day9PdfPath in $day9PdfPaths) {
    curl.exe --fail-with-body --silent --show-error `
        -X POST `
        "$day9BaseUrl/knowledge-bases/$day9KnowledgeBaseId/documents" `
        -F "file=@$day9PdfPath;type=application/pdf"
}

Invoke-RestMethod `
    -Method Get `
    -Uri "$day9BaseUrl/knowledge-bases/$day9KnowledgeBaseId/documents" |
    Select-Object id, filename, status, failure_reason
```

最后查询真实数据库，确认四份 ready 文档、页码范围和动态 Chunk 数。数据库用户名和库名从容器公开环境读取，不回显密码：

```powershell
$day9DbUser = (docker compose exec -T postgres printenv POSTGRES_USER).Trim()
$day9DbName = (docker compose exec -T postgres printenv POSTGRES_DB).Trim()
$day9Sql = @"
SELECT
    d.id,
    d.filename,
    d.status,
    COUNT(c.id) AS chunk_count,
    MIN(c.page_number) AS first_page,
    MAX(c.page_number) AS last_page
FROM documents AS d
LEFT JOIN chunks AS c ON c.document_id = d.id
WHERE d.knowledge_base_id = $day9KnowledgeBaseId
GROUP BY d.id, d.filename, d.status
ORDER BY d.id;
"@
docker compose exec -T postgres `
    psql -U $day9DbUser -d $day9DbName -c $day9Sql
```

### 预期状态码或输出结构

创建知识库预期 HTTP 201；每次上传预期 HTTP 201。单次上传稳定结构如下，所有数值和时间为动态值：

```json
{
  "document": {
    "id": "动态正整数",
    "knowledge_base_id": "与本次创建或复用的动态 ID 相同",
    "filename": "四个明确文件名之一",
    "status": "ready",
    "failure_reason": null,
    "created_at": "动态时间",
    "updated_at": "动态时间"
  },
  "page_count": 2,
  "chunk_count": "动态正整数"
}
```

数据库查询预期返回 4 行；每行 `status=ready`、`chunk_count>0`、`first_page=1`、`last_page=2`。

### 为什么它能证明今天已经完成

`--verify-only` 证明仓库中的二进制 PDF 与冻结清单一致，并且页级文字层和事实可提取；HTTP 201 和数据库查询进一步证明这 4 份固定语料能真实通过当前入库链路，产生带物理页码的 Chunk，而不只是“能打开的 PDF”。实际运行与记录是可选项，不影响计划文件本身的生成。

## 八、验证失败和边界路径

### 场景：YAML 中混入可联系邮箱时，生成器必须在写 PDF 前拒绝

以下命令只在系统临时目录创建一个明确的边界测试副本，不修改仓库事实源、不删除文件，也不接触数据库：

```powershell
$day9BoundaryRoot = Join-Path `
    ([System.IO.Path]::GetTempPath()) `
    'enterprise-rag-day9-boundary'
New-Item -ItemType Directory -Force -Path $day9BoundaryRoot | Out-Null

$day9BoundarySource = Join-Path `
    $day9BoundaryRoot `
    'policies-with-email.yaml'
Copy-Item `
    -LiteralPath 'data/demo_policies/policies.yaml' `
    -Destination $day9BoundarySource `
    -Force
Add-Content `
    -LiteralPath $day9BoundarySource `
    -Encoding utf8 `
    -Value "`nboundary_contact: demo.person@example.com"

$day9BoundaryOutput = Join-Path $day9BoundaryRoot 'pdfs'
$day9BoundaryManifest = Join-Path $day9BoundaryRoot 'manifest.json'
python scripts/generate_demo_pdfs.py `
    --source $day9BoundarySource `
    --output-dir $day9BoundaryOutput `
    --manifest $day9BoundaryManifest
$day9BoundaryExitCode = $LASTEXITCODE

if ($day9BoundaryExitCode -eq 0) {
    throw '边界验证失败：生成器没有拒绝邮箱模式'
}
if (Test-Path -LiteralPath $day9BoundaryOutput) {
    throw '边界验证失败：敏感扫描失败后仍创建了 PDF 输出目录'
}
Write-Host "边界验证通过，生成器退出码：$day9BoundaryExitCode"
```

### 预期结果

- HTTP 状态码或异常：不发送 HTTP；脚本应以退出码 1 结束，并只报告“演示数据疑似包含电子邮箱”这一类别。
- 数据库应该保留：原有知识库、Document、Chunk 和向量全部不变。
- 数据库不应该存在：不应因这次边界验证新增任何 Document 或 Chunk。
- 文件系统不应该存在：`$day9BoundaryOutput` 不应被创建，因为敏感扫描发生在输出目录创建之前。
- 响应不能泄露：错误不得回显匹配到的邮箱文本、真实本机秘密、数据库 URL、密码或堆栈。

另一个需要人工确认的边界是无答案空间：`policies.yaml` 和 4 份 PDF 中不应出现股权激励、海外签证补贴、VPN 授权、客户退款或生产事故流程的答案；今天只确认缺失，不把它们提前写成 Day 10 的正式测试集。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `ModuleNotFoundError: reportlab` | 没安装独立演示工具依赖，或安装到了另一个 Python | `python -m pip show reportlab`、`python -c "import sys; print(sys.executable)"` | 激活项目虚拟环境后执行 `python -m pip install -r requirements-demo.txt`，始终用同一个 `python` 运行脚本 |
| `未找到可嵌入的中文字体` | 默认 Windows/Linux 字体候选都不存在 | `Get-ChildItem -LiteralPath 'C:\Windows\Fonts' -File | Select-Object Name` | 选择许可允许嵌入且包含中文字符的 `.ttf`/`.ttc`，用 `--font-path '明确路径'` 运行；不要从不明来源下载字体 |
| `页数应为 2，实际为 3` | 某个 YAML 页面正文太长，ReportLab 自动溢出到下一页 | 错误中的明确 PDF 文件名；检查对应 `pages` 条目 | 精简该页重复说明，保留事实和标记后重新生成；不要放宽“两页”断言掩盖页码漂移 |
| `第 N 页缺少预期事实标记` | 字体映射导致无法提取中文，或标记被移动到另一物理页 | `python scripts/generate_demo_pdfs.py --verify-only`，再人工复制该页文字 | 优先更换可嵌入中文字体；确认 YAML 标记与同页正文完全一致后重新生成 |
| `现有 PDF 与 manifest.json 不一致` | PDF 被手工编辑、换字体重建，或只替换了部分输出 | `Get-FileHash -Algorithm SHA256 -LiteralPath '明确 PDF 路径'`，对照 `manifest.json` | 不直接编辑 PDF；确认内容变更意图，必要时升级 `corpus_version`，重新生成全部 4 份 PDF 和清单 |
| 上传返回 HTTP 400 且提示没有文字 | 生成文件没有可提取文字层，或上传了错误文件 | `python scripts/generate_demo_pdfs.py --verify-only`、核对 curl 的明确路径 | 只上传 `data/demo_policies/pdfs/` 中已经通过校验的文件；不要用截图或扫描件替代 |
| 上传返回 HTTP 500，文档为 `failed` | Embedding 模型、数据库或批量写入失败 | API 日志；`GET /knowledge-bases/{id}/documents`；查询 failed 文档 Chunk 数 | 先按 Day 8 的安全错误边界定位外部依赖；确认失败文档 Chunk 数为 0，再修复后重新上传，不修改 PDF 制造成功 |
| PDF 上传成功但数据库只有第 1 页 | 第二页没有正文、页数生成错误或查询范围写错 | `manifest.json` 的 `page_count`；数据库 `MIN/MAX(page_number)` | 先让 `--verify-only` 通过，再检查 SQL 使用正确知识库 ID；当前四份文档都应出现页码 1 和 2 |
| Git 看不到 PDF | 文件误放进被忽略的 `data/documents/` | `git check-ignore -v '明确 PDF 路径'` | 保持输出在 `data/demo_policies/pdfs/`；不要修改 `.gitignore` 让所有本地文档都被提交 |

## 十、检查最终代码差异

所有命令在项目根目录执行。新文件未暂存前，`git diff` 不显示其正文，所以必须同时看 `git status`、逐个读取文本文件，并核对 PDF 和清单：

```powershell
git status --short
git diff -- `
    requirements-demo.txt `
    data/demo_policies/policies.yaml `
    data/demo_policies/README.md `
    data/demo_policies/manifest.json `
    scripts/generate_demo_pdfs.py `
    docs/17天每日学习/Day09.md
python scripts/generate_demo_pdfs.py --verify-only
Get-FileHash -Algorithm SHA256 -LiteralPath `
    'data/demo_policies/pdfs/员工请假与考勤制度.pdf', `
    'data/demo_policies/pdfs/差旅与费用报销制度.pdf', `
    'data/demo_policies/pdfs/采购与办公资产管理制度.pdf', `
    'data/demo_policies/pdfs/访客与会议室管理办法.pdf'
```

重点检查：

- `policies.yaml` 只有虚构内容，没有真实组织名、姓名、邮箱、手机号、证件号、账号、密钥、连接串或内部资料。
- 每份 PDF 的两个物理页都能提取文字，页级标记没有漂移。
- 4 份文档至少覆盖人事、财务和行政，并有两个跨文档场景。
- 五个保留主题在 PDF 中没有答案，且没有提前生成 Day 10 的题目和标签。
- `manifest.json` 的 4 个 SHA-256 与 `Get-FileHash` 一致。
- 没有修改 `app/`、迁移、旧评测数据、`.env` 或 `data/documents/`。
- `git status` 不包含缓存、数据库文件或无关修改。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供上传、数据库查询或人工视觉验收结果。如果静态生成校验存在已知失败，应先修复再提交。

先按明确路径暂存，不使用 `git add .`：

```powershell
git add `
    requirements-demo.txt `
    data/demo_policies/policies.yaml `
    data/demo_policies/README.md `
    data/demo_policies/manifest.json `
    data/demo_policies/pdfs/员工请假与考勤制度.pdf `
    data/demo_policies/pdfs/差旅与费用报销制度.pdf `
    data/demo_policies/pdfs/采购与办公资产管理制度.pdf `
    data/demo_policies/pdfs/访客与会议室管理办法.pdf `
    scripts/generate_demo_pdfs.py `
    docs/17天每日学习/Day09.md
git diff --cached --stat
git diff --cached -- `
    requirements-demo.txt `
    data/demo_policies/policies.yaml `
    data/demo_policies/README.md `
    data/demo_policies/manifest.json `
    scripts/generate_demo_pdfs.py `
    docs/17天每日学习/Day09.md
git status --short
```

确认暂存区只包含当天文件后提交：

```powershell
git commit -m "Day9 add reproducible enterprise policy demo corpus"
```

二进制 PDF 只能在 `--verify-only` 通过、文件名正确且哈希已进入清单后暂存；不要提交边界验证产生的系统临时文件。

## 十二、面试高频问题与参考答案

### 问题 1：为什么不用真实公司制度做 RAG 演示数据？

#### 30 秒参考答案

真实制度往往包含内部流程、联系人、组织结构或版权边界，不适合进入公开仓库。我在当前项目中使用完全虚构的“星河协作科技有限公司”制度语料，保留企业文档的章节、审批、期限和跨文档关系，同时在生成前扫描邮箱、手机号、身份证、银行卡、API Key 和数据库连接串。这样既能覆盖检索和拒答场景，也能安全公开和重复演示。

#### 继续追问：只做正则扫描就足够安全吗？

不够。正则只能发现结构明显的风险项，不能判断一段真实制度是否被改名后复制。因此我的边界是“源头完全合成 + 正则扫描 + YAML 人工审查 + PDF 人工抽查”。扫描是自动防线，不代替内容治理。

#### 回答时要引用的项目依据

- `data/demo_policies/policies.yaml` 的 `organization`、`fictional_notice` 与全部合成条款。
- `scripts/generate_demo_pdfs.py` 的 `SENSITIVE_PATTERNS` 和 `scan_sensitive_data()`。
- `data/demo_policies/README.md` 的冻结规则与禁止范围。

### 问题 2：为什么评测前必须冻结 PDF 版本？

#### 30 秒参考答案

如果看到模型答错后再修改 PDF，评测集就会反向泄漏到数据中，前后实验也不再可比。我把 YAML 作为唯一事实源，用 `corpus_version` 标识语料版本，并在 `manifest.json` 记录每份 PDF 的 SHA-256、页数和文字数。Day 10 的题目会引用这个固定版本；任何内容变化都必须升级版本并重新核对证据。

#### 继续追问：为什么文件名和 Git commit 还不够？

同一个文件名可以对应不同字节，甚至换字体或版式就可能改变提取结果和 Chunk 边界。Git commit 可以定位仓库状态，SHA-256 则直接校验当前文件内容；二者一起让数据版本和实际运行输入都可追踪。

#### 回答时要引用的项目依据

- `data/demo_policies/policies.yaml` 的 `corpus_version`。
- `data/demo_policies/manifest.json` 的 `sha256`、`page_count` 和 `page_text_characters`。
- `scripts/generate_demo_pdfs.py` 的 `sha256_file()` 与 `verify_frozen_manifest()`。

### 问题 3：这批演示数据怎样覆盖多文档检索和来源追溯？

#### 30 秒参考答案

我设计了四份边界清楚的制度：人事、差旅报销、采购资产和访客会议。出差场景需要同时查人事考勤与财务报销，设备采购场景需要同时查采购验收、资产登记与财务付款凭证。每份 PDF 固定两页，每页有两个事实标记，生成后用 pypdf 回读指定物理页。当前入库链路再把该页码保存到 Chunk，问答响应可以返回文件名、页码、Chunk 原文和分数。

#### 继续追问：为什么不把所有制度写在一个 PDF？

单 PDF 无法充分验证多文档管理、文件名来源、跨文档整合和文档边界。拆成四份后既能问单文档事实，也能观察 Top-K 是否从两个相关文件取证；同时各文档主题清楚，便于定位错误来自检索还是生成。

#### 回答时要引用的项目依据

- `data/demo_policies/README.md` 的文件覆盖表和跨文档场景。
- `app/services/document_ingestion_service.py` 的按页切块与 `page_number` 写入。
- `app/models.py` 的 `KnowledgeBaseQuerySource` 来源字段。

### 问题 4：怎样设计无答案数据，而不是只测试系统会回答的问题？

#### 30 秒参考答案

我在建语料时显式定义“覆盖空间”和“无答案空间”。当前四份制度覆盖考勤、报销、采购和访客管理，但刻意不写股权激励、海外签证补贴、VPN、客户退款和生产事故流程。Day 10 会从这些缺失主题建立拒答用例，因此拒答不是随手挑一个怪问题，而是相对于固定语料边界进行评估。

#### 继续追问：今天为什么不直接写无答案题？

因为 Day 9 的唯一产物是冻结文档。只有 PDF 页码、提取文本和哈希稳定后，Day 10 才能系统地标注至少 12 道可回答题和 6 道无答案题；提前写题会把两个阶段混在一起，并可能引用尚未稳定的证据。

#### 回答时要引用的项目依据

- `data/demo_policies/policies.yaml` 的 `reserved_absent_topics`。
- `data/demo_policies/README.md` 的“明确保留的无答案空间”。
- `app/services/database_rag_service.py` 的 `MIN_RELEVANCE_SCORE` 与拒答结构；今天不调整该阈值。

### 问题 5：如何证明 PDF 真的适合 RAG 入库，而不只是能打开？

#### 30 秒参考答案

能打开只证明阅读器接受文件，不证明后端能提取文本。我分两层验证：生成器用当前同款 pypdf 按页回读，断言两页都有文字并包含预期事实标记；然后可选地通过真实上传 API 入库，查询数据库确认四份文档都是 ready、Chunk 数大于零，并且每份都有 page_number 1 和 2。这样同时覆盖静态文件和真实入库链路。

#### 继续追问：为什么还要人工视觉抽查？

文字提取正确不代表视觉布局一定正确，例如段落可能重叠或页脚被遮挡。自动校验负责可机器检索性，人工抽查负责演示可读性，两者关注的失败模式不同。

#### 回答时要引用的项目依据

- `scripts/generate_demo_pdfs.py` 的 `inspect_pdf()`。
- `app/services/pdf_service.py` 的 `_extract_text()`。
- 第七部分 HTTP 上传与数据库 `MIN/MAX(page_number)` 查询。

## 十三、今天的完整数据流

### 正常路径

```text
虚构制度事实与覆盖边界
→ data/demo_policies/policies.yaml
→ 结构校验 + 敏感模式扫描
→ ReportLab 使用可嵌入中文字体生成 4 份 PDF
→ pypdf 按物理页回读文字
→ 校验每份恰好 2 页、每页命中预期事实
→ 计算 SHA-256 并写 manifest.json
→ --verify-only 对 PDF 与冻结清单再次比对
→ 可选：上传到同一 KnowledgeBase
→ PDFService 按页提取
→ DocumentIngestionService 按 200/40 切 Chunk 并生成 512 维向量
→ PostgreSQL 保存 4 个 ready Document 与带 page_number 的 Chunk
```

### 失败路径

```text
YAML 结构错误 / 标记错页 / 敏感模式
→ validate_source 在创建输出目录前失败
→ 退出码 1
→ 不生成 PDF、不写 manifest、不访问数据库
```

```text
字体缺失 / 版式溢出 / 文字层不可提取
→ PDF 构建或 inspect_pdf 失败
→ 退出码 1
→ 不把失败结果视为冻结语料
→ 修正字体或源内容后重新生成全部已知输出
```

```text
PDF 入库时解析 / Embedding / 数据库写入失败
→ Day 8 事务边界 rollback Chunk 与 ready 更新
→ Document 以安全 failed 状态保存
→ 失败文档 Chunk 数为 0，不能参与 ready 检索
```

## 十四、完成标准

```text
[ ] 能解释“完全合成 + 自动敏感扫描 + 人工复核”为什么缺一不可
[ ] 能解释为什么必须先冻结语料版本，再在 Day 10 标注问题与证据
[ ] 已创建 policies.yaml、生成/校验脚本、独立工具依赖和语料 README
[ ] 已由脚本生成 4 份明确命名的企业制度 PDF，每份恰好 2 页并含可提取文字层
[ ] manifest.json 记录语料版本、4 个 SHA-256、页数和每页文字字符数
[ ] 至少覆盖人事、财务、采购/行政三个领域，以及两个需要组合来源的跨文档场景
[ ] 明确保留至少五个无答案主题，没有提前生成 Day 10 正式题集或调整 Day 11 参数
[ ] 已提供 --verify-only、HTTP 上传和数据库查询命令及预期结果，实际执行与记录可选
[ ] 已提供“混入邮箱必须在写 PDF 前失败”的边界命令及预期结果，实际执行与记录可选
[ ] 能不看代码复述“YAML → 敏感扫描 → PDF → 按页回读 → 哈希清单 → 可选入库”的完整数据流
[ ] git diff 和暂存区只包含 Day 9 的明确文本、PDF、清单与计划，不包含秘密、数据库文件或无关修改
[ ] 核心语料生成并通过静态校验后可执行边界清晰的 Git commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
