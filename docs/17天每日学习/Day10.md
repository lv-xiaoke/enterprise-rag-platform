# Day 10：建立新的企业制度固定评测集

今天将直接建立一套与 4 份冻结企业制度 PDF 对齐的固定评测集，使项目获得可重复比较检索、回答与拒答质量的统一输入，并为面试中的 Ground truth、数据泄漏和离线评测设计问题提供项目依据。

> 预计核心用时：约 60 分钟  
> 今日唯一核心产物：一套版本固定、包含 12 道可回答题、6 道无答案题及可离线校验证据标签的企业制度评测数据集  
> 当前真实状态：已完成 
> 对应总体安排：Day 10

## 一、今天完成后的项目变化

### 升级前

```text
data/evaluation/questions.json
→ 只面向旧的单 PDF FAISS 基线
→ 题目与 Day 9 的 4 份企业制度 PDF 无关
→ 不能作为数据库版多知识库 RAG 的新评测输入

data/demo_policies/manifest.json
→ 已冻结 4 份 PDF 的版本、页数和 SHA-256
→ 尚无逐题 Ground truth、证据页和拒答标签
```

### 升级后

```text
Day 9 冻结 manifest + 4 份 PDF
→ data/evaluation/enterprise_questions.json
→ 12 道可回答题 + 6 道无答案题
→ 直接事实 / 综合 / 跨文档 / 相似内容隔离 / 无答案
→ 每道可回答题固定文件名、页码和原文锚点
→ 每道无答案题固定拒答标签与保留缺失主题
→ scripts/validate_enterprise_questions.py 离线校验
→ Day 11 可以在不改题的前提下比较 Top-K、阈值和指标
```

### 今天在完整项目中的位置

- 所属阶段：可靠性与数据。
- 所属链路：检索、回答与拒答的质量标准。
- 今天的输入：Day 9 的 `2026-09-04-v1` 冻结语料、4 份 PDF、`manifest.json`、当前 `top_k=3` 与拒答阈值 `0.55`。
- 今天的输出：`enterprise_questions.json` 固定评测输入，以及只读取 JSON、manifest 和 PDF 的离线校验脚本。
- 下一天为什么需要它：Day 11 必须使用不随实验结果变化的题目和标签，才能计算可比较的 Recall@1/3/5、MRR、拒答正确率和延迟。

## 二、开始前的真实状态

### 已经具备

- `[当前事实]` `data/demo_policies/manifest.json` 冻结了语料版本 `2026-09-04-v1`、4 个 PDF 文件名、每份 2 页及各自 SHA-256。
- `[当前事实]` 4 份 PDF 覆盖人事、财务、采购与行政，并明确保留两个跨文档场景。
- `[当前事实]` `data/demo_policies/policies.yaml` 明确保留股权激励、海外出差、VPN、客户合同退款和灾难恢复等无答案空间。
- `[当前事实]` `app/models.py` 的数据库版问答响应包含 `answer`、`refused` 和可追溯到 `chunk_id`、`document_id`、文件名、页码、Chunk 原文与分数的 `sources`。
- `[当前事实]` `app/services/database_rag_service.py` 当前参考拒答阈值为 `0.55`，固定拒答文本为“当前知识库中没有找到足够的信息。”。
- `[当前事实]` `app/services/retrieval_service.py` 当前默认 `top_k=3`，允许范围为 1～10。
- `[当前事实]` Day 1～Day 9 均有核心代码或数据产物、用户完成标记和相匹配提交；最新 Day 9 提交为 `4845d4e`。
- `[当前事实]` 生成本计划前 `git status --short` 没有输出，工作区无已识别的未提交修改。

### 仍然缺少

- `[当前事实]` 尚不存在 `data/evaluation/enterprise_questions.json`。
- `[当前事实]` 尚无面向 4 份企业制度 PDF 的 12 道可回答题和 6 道无答案题。
- `[当前事实]` 尚无逐题固定的答案要点、证据文件、证据页、原文锚点和拒答标签。
- `[当前事实]` 尚无自动检查题目数量、类别覆盖、PDF 哈希、证据页和原文锚点的脚本。
- `[当前事实]` 旧 `data/evaluation/questions.json` 与 `scripts/run_evaluation.py` 仍属于单 PDF FAISS 基线，不能当作新系统已经完成评测的证据。

### 待实测

- `[待实测]` 当前学习数据库中是否已经把 4 份 Day 9 PDF 上传到同一个知识库，以及实际生成的 `document_id`、`chunk_id` 和 Chunk 数量。
- `[待实测]` Day 11 使用不同 Top-K 和阈值时，各题的检索排名、相似度、拒答结果和延迟。
- `[待实测]` LLM 对答案要点的覆盖情况；今天只冻结 Ground truth，不提前声称模型回答正确。

### 需要保护的用户修改

- 当前 `git status --short` 为空；仍只按当天文件清单操作，不修改旧评测结果、应用代码、迁移、演示 PDF 或其他学习笔记。

## 三、今天必须理解的核心知识

### 1. Ground truth 与模型回答不是同一件事

- 一句话解释：Ground truth 是实验前人工冻结的判定标准，模型回答是实验运行后产生的待评对象。
- 在当前项目中的职责：`expected_points` 和 `expected_evidence` 是 Ground truth；Day 11 产生的回答、来源、分数和延迟属于运行结果。
- 与其他组件的关系：固定标签供评测脚本计算检索命中、排名和拒答是否正确，但不能被模型运行结果反向改写。
- 容易混淆的点：模型措辞不必与 `expected_answer` 完全一致，只要覆盖关键要点且来源正确；反过来，语言流畅也不能替代证据命中。
- 面试一句话：我把预期答案要点和证据定位在实验前冻结，模型输出单独保存，从数据结构上避免“用预测结果改标准答案”。

### 2. 稳定证据定位与动态数据库 ID

- 一句话解释：可重复评测需要跨重建仍稳定的证据标识，而数据库自增 ID 会随重新入库变化。
- 在当前项目中的职责：今天使用 PDF 文件名、物理页码和原文锚点固定证据；运行时返回的 `document_id`、`chunk_id` 由 Day 11 记录，但不写死进数据集。
- 与其他组件的关系：`DocumentIngestionService` 每次入库会创建新的 Document 和 Chunk；`KnowledgeBaseQuerySource` 再把当次 ID、文件名、页码和原文返回。
- 容易混淆的点：Chunk ID 适合定位一次数据库运行，文件哈希 + 文件名 + 页码 + 原文锚点才适合冻结跨环境 Ground truth。
- 面试一句话：我没有把自增 Chunk ID 当永久标签，而是用冻结 PDF 哈希和页级原文锚点做稳定标签，再在运行结果中保留实际 Chunk ID 供排查。

### 3. 题型分层与数据泄漏

- 一句话解释：评测集要覆盖不同失败模式，而且题目必须在调参前冻结。
- 在当前项目中的职责：12 道可回答题分为直接事实、综合、跨文档和相似内容隔离；6 道无答案题来自 Day 9 预留的缺失主题。
- 与其他组件的关系：直接事实主要验证单个证据召回，跨文档题验证多个来源，隔离题验证相近金额、期限或流程不会串线，无答案题验证阈值拒答。
- 容易混淆的点：看到 Day 11 某题没命中后立即改问题或证据，会让不同参数不再面对同一测试集，形成评测数据泄漏。
- 面试一句话：我先冻结题目、语料哈希和证据，再调 Top-K 与阈值，避免为了当前参数临时改题导致指标失真。

### 4. 检索命中、答案正确和拒答正确是三个维度

- 一句话解释：找到正确证据、依据证据回答、在无证据时拒答是三个相关但不能互相替代的判断。
- 在当前项目中的职责：`expected_evidence` 支撑 Recall/MRR，`expected_points` 支撑答案要点检查，`expected_refusal` 支撑无答案正确率。
- 与其他组件的关系：pgvector 返回候选 Chunk，`DatabaseRAGService` 用 `0.55` 过滤证据，LLM 只在存在可靠证据时生成回答。
- 容易混淆的点：无答案题仍会被向量数据库返回 Top-K 候选；候选存在不代表有可靠答案，必须结合阈值和拒答标签判断。
- 面试一句话：我的评测把检索、生成和拒答拆开记录，所以能区分“没召回”“召回了但答错”和“本应拒答却编造”三类问题。

## 四、升级涉及的文件

| 文件                                          | 操作     | 作用                                       |
| ------------------------------------------- | ------ | ---------------------------------------- |
| `data/evaluation/enterprise_questions.json` | 新建     | 冻结语料版本、参数候选、18 道题、答案要点、证据锚点和拒答标签         |
| `scripts/validate_enterprise_questions.py`  | 新建     | 离线校验 JSON 结构、数量、类别、PDF 哈希、证据页、原文锚点和无答案主题 |
| `docs/17天每日学习/Day10.md`                     | 已生成，保留 | 今日升级手册与可选执行记录                            |

### 今日不做

- 不修改 `data/evaluation/questions.json`、`baseline_results.json` 或 `top_k_comparison.json`，它们继续保留为旧单 PDF 基线。
- 不改造 `scripts/run_evaluation.py`，不计算 Recall、MRR、拒答正确率或延迟；这些属于 Day 11。
- 不根据任何试跑结果修改问题、证据或阈值候选。
- 不修改上传、检索、RAG、事务、ORM 或迁移。
- 不新增 pytest；关键自动化测试属于 Day 12。

## 五、按顺序完成项目升级

### 步骤 1：新建固定评测数据集（建议 25 分钟）

**目标**

把 Day 9 的冻结语料转成一个只包含评测输入和 Ground truth、不混入模型运行结果的版本化 JSON。

**修改位置**

- 文件：`data/evaluation/enterprise_questions.json`
- 定位：当天新建文件，不覆盖现有 `questions.json`
- 操作：新建并复制完整 JSON

**复制下面的完整代码**

```json
{
  "schema_version": 1,
  "dataset_version": "2026-09-04-v1",
  "corpus": {
    "manifest_path": "data/demo_policies/manifest.json",
    "pdf_directory": "data/demo_policies/pdfs",
    "corpus_version": "2026-09-04-v1",
    "document_count": 4,
    "documents": [
      {
        "filename": "员工请假与考勤制度.pdf",
        "sha256": "7b8a903bf96df31acdb22b0185c28ec8ea56935bfcc88e40de34f140ffddebe8"
      },
      {
        "filename": "差旅与费用报销制度.pdf",
        "sha256": "8987569d8f6ad10804b8e842de8400336621496cc53cefc34c7fb2be94d84b26"
      },
      {
        "filename": "采购与办公资产管理制度.pdf",
        "sha256": "ce1959414db895d26c6069b4ff4c2b73069951c60c3380b3f87abd591b16fe6a"
      },
      {
        "filename": "访客与会议室管理办法.pdf",
        "sha256": "1913d80b4ffbd2ec7783962344ff1802ee43463624af2de4baaaf67d13bc0bc4"
      }
    ]
  },
  "evaluation": {
    "default_top_k": 3,
    "top_k_candidates": [
      1,
      3,
      5
    ],
    "current_reference_threshold": 0.55,
    "threshold_candidates": [
      0.45,
      0.55,
      0.65
    ],
    "score_semantics": "cosine_similarity_higher_is_better",
    "answerable_minimum": 12,
    "unanswerable_minimum": 6,
    "required_answerable_categories": [
      "direct_fact",
      "comprehensive",
      "cross_document",
      "isolation"
    ]
  },
  "cases": [
    {
      "id": "direct-leave-01",
      "category": "direct_fact",
      "question": "连续三天以上的年假需要提前多久申请，并经过哪些确认？",
      "answerable": true,
      "expected_answer": "连续三天以上年假须至少提前七个工作日申请，先由直属负责人确认工作交接，再由人力资源部核对可用假期。",
      "expected_points": [
        "至少提前七个工作日",
        "直属负责人确认工作交接",
        "人力资源部核对可用假期"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "员工请假与考勤制度.pdf",
          "page_number": 1,
          "evidence_contains": "连续三天以上年假须至少提前七个工作日申请"
        },
        {
          "filename": "员工请假与考勤制度.pdf",
          "page_number": 1,
          "evidence_contains": "申请先由直属负责人确认工作交接，再由人力资源部核对可用假期"
        }
      ]
    },
    {
      "id": "direct-sick-leave-01",
      "category": "direct_fact",
      "question": "病假超过一个工作日需要补充什么材料，最晚何时补充？",
      "answerable": true,
      "expected_answer": "病假超过一个工作日须提交医疗机构证明，并在返岗后的两个工作日内补充。",
      "expected_points": [
        "医疗机构证明",
        "返岗后的两个工作日内"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "员工请假与考勤制度.pdf",
          "page_number": 2,
          "evidence_contains": "病假超过一个工作日须提交医疗机构证明，证明应在返岗后的两个工作日内补充"
        }
      ]
    },
    {
      "id": "isolation-annual-leave-01",
      "category": "isolation",
      "question": "一天以内年假和连续三天以上年假的提前申请要求分别是什么？",
      "answerable": true,
      "expected_answer": "一天以内年假至少提前三个工作日申请；连续三天以上年假至少提前七个工作日申请。",
      "expected_points": [
        "一天以内至少提前三个工作日",
        "连续三天以上至少提前七个工作日"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "员工请假与考勤制度.pdf",
          "page_number": 1,
          "evidence_contains": "一天以内的年假应至少提前三个工作日在系统提交"
        },
        {
          "filename": "员工请假与考勤制度.pdf",
          "page_number": 1,
          "evidence_contains": "连续三天以上年假须至少提前七个工作日申请"
        }
      ]
    },
    {
      "id": "cross-trip-01",
      "category": "cross_document",
      "question": "员工因公出差时，从出发前到返程后，为了考勤和报销需要完成哪些关键步骤？",
      "answerable": true,
      "expected_answer": "员工应在出发前提交并完成差旅审批；审批完成的出差日期按正常出勤登记且无需重复外勤签到；返程后十个工作日内提交已批准的差旅申请、费用明细和合法有效发票进行报销。",
      "expected_points": [
        "出发前提交差旅申请",
        "审批完成的出差日期按正常出勤登记",
        "无需重复提交外勤签到",
        "返程后十个工作日内提交报销",
        "已批准的差旅申请、费用明细和合法有效发票"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "员工请假与考勤制度.pdf",
          "page_number": 2,
          "evidence_contains": "审批完成的出差日期按正常出勤登记，出差期间无需重复提交外勤签到"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 1,
          "evidence_contains": "员工因公出差应在出发前提交差旅申请"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 2,
          "evidence_contains": "员工应在返程后十个工作日内提交报销"
        }
      ]
    },
    {
      "id": "direct-hotel-01",
      "category": "direct_fact",
      "question": "境内出差时，一线城市和其他城市的住宿上限分别是多少？",
      "answerable": true,
      "expected_answer": "一线城市住宿上限为每晚六百元，其他城市住宿上限为每晚四百五十元。",
      "expected_points": [
        "一线城市每晚六百元",
        "其他城市每晚四百五十元"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 1,
          "evidence_contains": "一线城市住宿上限为每晚六百元，其他城市住宿上限为每晚四百五十元"
        }
      ]
    },
    {
      "id": "isolation-travel-allowance-01",
      "category": "isolation",
      "question": "市内交通补助和出差餐费补助的每日上限分别是多少？",
      "answerable": true,
      "expected_answer": "市内交通补助上限为每日八十元，出差餐费补助上限为每日一百元。",
      "expected_points": [
        "市内交通每日八十元",
        "餐费每日一百元"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 1,
          "evidence_contains": "市内交通补助上限为每日八十元"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 1,
          "evidence_contains": "出差餐费补助上限为每日一百元"
        }
      ]
    },
    {
      "id": "comprehensive-reimbursement-01",
      "category": "comprehensive",
      "question": "员工返程后提交报销需要哪些材料，财务复核和付款分别需要多久？",
      "answerable": true,
      "expected_answer": "员工应在返程后十个工作日内提交已批准的差旅申请、费用明细和合法有效发票；财务复核在五个工作日内完成，通过复核后在三个工作日内进入付款流程。",
      "expected_points": [
        "返程后十个工作日内",
        "已批准的差旅申请",
        "费用明细",
        "合法有效的发票",
        "财务复核五个工作日",
        "通过复核后三个工作日内进入付款流程"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 2,
          "evidence_contains": "材料包括已批准的差旅申请、费用明细和合法有效的发票"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 2,
          "evidence_contains": "财务复核在五个工作日内完成"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 2,
          "evidence_contains": "通过复核的报销在三个工作日内进入付款流程"
        }
      ]
    },
    {
      "id": "comprehensive-procurement-tier-01",
      "category": "comprehensive",
      "question": "办公采购在一千元以内、一千元以上至五千元以及超过五千元时，审批和报价要求有什么区别？",
      "answerable": true,
      "expected_answer": "一千元以内由申请人直属负责人审批；超过一千元且不超过五千元需要至少两家供应商报价并由部门负责人批准；超过五千元需要三家供应商报价，并由部门负责人和财务负责人共同确认预算。",
      "expected_points": [
        "一千元以内由直属负责人审批",
        "超过一千元且不超过五千元至少两家报价",
        "超过一千元且不超过五千元由部门负责人批准",
        "超过五千元三家报价",
        "部门负责人和财务负责人共同确认预算"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "采购与办公资产管理制度.pdf",
          "page_number": 1,
          "evidence_contains": "单次采购金额一千元以内由申请人直属负责人审批"
        },
        {
          "filename": "采购与办公资产管理制度.pdf",
          "page_number": 1,
          "evidence_contains": "超过一千元且不超过五千元的采购，需要至少两家供应商报价并由部门负责人批准"
        },
        {
          "filename": "采购与办公资产管理制度.pdf",
          "page_number": 1,
          "evidence_contains": "单次采购金额超过五千元须取得三家供应商报价，并由部门负责人和财务负责人共同确认预算"
        }
      ]
    },
    {
      "id": "cross-procurement-payment-01",
      "category": "cross_document",
      "question": "办公设备到货后，要完成资产登记并进入财务付款，需要经过哪些关键动作和凭证？",
      "answerable": true,
      "expected_answer": "申请人和资产管理员应在到货后两个工作日内完成验收；达到固定资产登记标准的设备由行政部门登记资产信息；验收通过后汇总采购审批、报价、验收记录和合法发票交财务复核，缺少验收记录时财务不发起付款。",
      "expected_points": [
        "到货后两个工作日内完成验收",
        "行政部门登记资产信息",
        "采购审批记录",
        "报价或比价记录",
        "到货验收记录",
        "合法发票",
        "缺少验收记录不发起付款"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "采购与办公资产管理制度.pdf",
          "page_number": 2,
          "evidence_contains": "申请人和资产管理员应在到货后两个工作日内完成验收"
        },
        {
          "filename": "采购与办公资产管理制度.pdf",
          "page_number": 2,
          "evidence_contains": "达到固定资产登记标准的设备，由行政部门登记资产编号、所属部门、保管角色和领用日期"
        },
        {
          "filename": "采购与办公资产管理制度.pdf",
          "page_number": 2,
          "evidence_contains": "采购组在验收通过后汇总审批记录、报价记录、验收记录和发票，交财务部进行付款复核"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 2,
          "evidence_contains": "办公设备采购付款应同时附采购审批记录、供应商报价或比价记录、到货验收记录和合法发票"
        },
        {
          "filename": "差旅与费用报销制度.pdf",
          "page_number": 2,
          "evidence_contains": "缺少验收记录时，财务部暂不发起付款"
        }
      ]
    },
    {
      "id": "direct-visitor-01",
      "category": "direct_fact",
      "question": "外部访客进入办公区需要提前多久登记，登记哪些信息？",
      "answerable": true,
      "expected_answer": "外部访客须至少提前一个工作日登记，由接待部门填写来访单位类别、来访目的、预计时间、人数和接待角色。",
      "expected_points": [
        "至少提前一个工作日",
        "来访单位类别",
        "来访目的",
        "预计时间",
        "人数",
        "接待角色"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "访客与会议室管理办法.pdf",
          "page_number": 1,
          "evidence_contains": "外部访客须至少提前一个工作日登记"
        },
        {
          "filename": "访客与会议室管理办法.pdf",
          "page_number": 1,
          "evidence_contains": "由接待部门填写来访单位类别、来访目的、预计时间、人数和接待角色"
        }
      ]
    },
    {
      "id": "isolation-visitor-meeting-01",
      "category": "isolation",
      "question": "接待外部访客开会时，只预订会议室是否足够？还需要做什么？",
      "answerable": true,
      "expected_answer": "不够；必须同时完成访客登记和会议室预订，会议室预订不能替代访客预约。",
      "expected_points": [
        "同时完成访客登记和会议室预订",
        "会议室预订不能替代访客预约"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "访客与会议室管理办法.pdf",
          "page_number": 2,
          "evidence_contains": "接待外部访客时须同时完成访客登记和会议室预订"
        },
        {
          "filename": "访客与会议室管理办法.pdf",
          "page_number": 2,
          "evidence_contains": "会议室预订本身不能替代访客预约"
        }
      ]
    },
    {
      "id": "comprehensive-meeting-01",
      "category": "comprehensive",
      "question": "会议取消时应提前多久释放会议室，连续两次未使用且未取消会有什么后果？",
      "answerable": true,
      "expected_answer": "应在会议开始前两小时取消预订；连续两次未使用且未取消时，行政部可以暂停该组织者一周的提前预订权限。",
      "expected_points": [
        "会议开始前两小时取消",
        "连续两次未使用且未取消",
        "暂停一周提前预订权限"
      ],
      "expected_refusal": false,
      "expected_evidence": [
        {
          "filename": "访客与会议室管理办法.pdf",
          "page_number": 2,
          "evidence_contains": "应在会议开始前两小时取消预订"
        },
        {
          "filename": "访客与会议室管理办法.pdf",
          "page_number": 2,
          "evidence_contains": "连续两次未使用且未取消的，行政部可以暂停该组织者一周的提前预订权限"
        }
      ]
    },
    {
      "id": "unknown-equity-01",
      "category": "unanswerable",
      "question": "公司的股票期权归属周期和行权条件是什么？",
      "answerable": false,
      "expected_answer": "当前知识库中没有找到足够的信息。",
      "expected_points": [
        "明确拒答",
        "不编造归属周期或行权条件",
        "不返回伪造来源"
      ],
      "expected_refusal": true,
      "absent_topic": "股权激励与股票期权归属",
      "expected_evidence": []
    },
    {
      "id": "unknown-overseas-visa-01",
      "category": "unanswerable",
      "question": "员工去海外出差时，公司如何办理签证？",
      "answerable": false,
      "expected_answer": "当前知识库中没有找到足够的信息。",
      "expected_points": [
        "明确拒答",
        "不编造签证办理流程",
        "不返回伪造来源"
      ],
      "expected_refusal": true,
      "absent_topic": "海外出差签证与境外补贴",
      "expected_evidence": []
    },
    {
      "id": "unknown-overseas-allowance-01",
      "category": "unanswerable",
      "question": "海外出差的境外住宿和每日补贴标准是多少？",
      "answerable": false,
      "expected_answer": "当前知识库中没有找到足够的信息。",
      "expected_points": [
        "明确拒答",
        "不把境内差旅标准当成境外标准",
        "不返回伪造来源"
      ],
      "expected_refusal": true,
      "absent_topic": "海外出差签证与境外补贴",
      "expected_evidence": []
    },
    {
      "id": "unknown-vpn-01",
      "category": "unanswerable",
      "question": "员工申请 VPN 远程接入需要经过哪些信息安全审批？",
      "answerable": false,
      "expected_answer": "当前知识库中没有找到足够的信息。",
      "expected_points": [
        "明确拒答",
        "不编造 VPN 或信息安全审批",
        "不返回伪造来源"
      ],
      "expected_refusal": true,
      "absent_topic": "远程接入、VPN 与信息安全授权",
      "expected_evidence": []
    },
    {
      "id": "unknown-contract-refund-01",
      "category": "unanswerable",
      "question": "客户要求合同退款时，退款比例和违约赔偿如何计算？",
      "answerable": false,
      "expected_answer": "当前知识库中没有找到足够的信息。",
      "expected_points": [
        "明确拒答",
        "不编造退款比例或赔偿公式",
        "不返回伪造来源"
      ],
      "expected_refusal": true,
      "absent_topic": "客户合同退款与违约赔偿",
      "expected_evidence": []
    },
    {
      "id": "unknown-disaster-recovery-01",
      "category": "unanswerable",
      "question": "生产事故发生后，系统的灾难恢复 RTO 和 RPO 分别是多少？",
      "answerable": false,
      "expected_answer": "当前知识库中没有找到足够的信息。",
      "expected_points": [
        "明确拒答",
        "不编造 RTO 或 RPO",
        "不返回伪造来源"
      ],
      "expected_refusal": true,
      "absent_topic": "生产事故响应与灾难恢复",
      "expected_evidence": []
    }
  ]
}
```

**这段代码怎样工作**

- 输入：Day 9 的 `manifest.json`、4 份 PDF 和当前检索配置常量。
- 输出：18 个固定 case，其中 12 个 `answerable=true`，6 个 `expected_refusal=true`。
- 调用谁：该 JSON 不直接调用应用；Day 10 校验脚本读取它，Day 11 评测脚本也将读取它。
- 被谁调用：`scripts/validate_enterprise_questions.py` 和后续 Day 11 的新版评测脚本。
- 正常路径：可回答题用一个或多个 `expected_evidence` 定位正确文件、页码和原文；无答案题用 `absent_topic` 对齐 manifest 的保留缺失主题。
- 失败路径：语料版本、PDF 哈希、证据页、证据原文、题目数量或拒答标签不一致时，校验脚本退出码为 1。
- 稳定性设计：数据集中不保存 `retrieved_sources`、`model_answer`、实时分数或自增 Chunk ID，避免运行结果污染固定输入。

**完成本步骤后的预期状态**

- 新文件能被标准 JSON 解析器读取。
- 题型分布为：直接事实 4、综合 3、跨文档 2、隔离 3、无答案 6。
- 旧单 PDF `questions.json` 未被覆盖。

### 步骤 2：新建离线数据集校验器（建议 20 分钟）

**目标**

用一个不调用数据库、Embedding 或 LLM 的确定性脚本，验证评测集确实绑定冻结语料并满足 Day 10 的数量与标签约束。

**修改位置**

- 文件：`scripts/validate_enterprise_questions.py`
- 定位：当天新建文件
- 操作：新建并复制完整 Python 实现

**复制下面的完整代码**

```python
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    PROJECT_ROOT / "data" / "evaluation" / "enterprise_questions.json"
)
ALLOWED_CATEGORIES = {
    "direct_fact",
    "comprehensive",
    "cross_document",
    "isolation",
    "unanswerable",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="校验 Day 10 企业制度固定评测集。"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="评测集 JSON 路径。",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"找不到 JSON 文件：{path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 根节点必须是对象：{path}")
    return payload


def require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} 必须是对象")
    return value


def require_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} 必须是数组")
    return value


def require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 必须是非空字符串")
    return value.strip()


def resolve_project_path(value: Any, field_name: str) -> Path:
    relative_path = Path(require_non_empty_string(value, field_name))
    if relative_path.is_absolute():
        raise ValueError(f"{field_name} 必须是项目内相对路径")
    resolved_path = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT != resolved_path and PROJECT_ROOT not in resolved_path.parents:
        raise ValueError(f"{field_name} 不能指向项目目录之外")
    return resolved_path


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_candidates(evaluation: dict[str, Any]) -> None:
    top_k_candidates = require_list(
        evaluation.get("top_k_candidates"),
        "evaluation.top_k_candidates",
    )
    if (
        not top_k_candidates
        or any(type(value) is not int for value in top_k_candidates)
        or any(value < 1 or value > 10 for value in top_k_candidates)
        or top_k_candidates != sorted(set(top_k_candidates))
    ):
        raise ValueError(
            "evaluation.top_k_candidates 必须是 1 到 10 内的升序唯一整数"
        )

    default_top_k = evaluation.get("default_top_k")
    if default_top_k not in top_k_candidates:
        raise ValueError("evaluation.default_top_k 必须属于 top_k_candidates")

    threshold_candidates = require_list(
        evaluation.get("threshold_candidates"),
        "evaluation.threshold_candidates",
    )
    if not threshold_candidates:
        raise ValueError("evaluation.threshold_candidates 不能为空")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in threshold_candidates
    ):
        raise ValueError("threshold_candidates 只能包含数字")
    normalized_thresholds = [float(value) for value in threshold_candidates]
    if (
        any(value < -1.0 or value > 1.0 for value in normalized_thresholds)
        or normalized_thresholds != sorted(set(normalized_thresholds))
    ):
        raise ValueError("threshold_candidates 必须是 -1 到 1 内的升序唯一数字")

    reference_threshold = evaluation.get("current_reference_threshold")
    if (
        isinstance(reference_threshold, bool)
        or not isinstance(reference_threshold, (int, float))
        or float(reference_threshold) not in normalized_thresholds
    ):
        raise ValueError(
            "current_reference_threshold 必须属于 threshold_candidates"
        )

    if evaluation.get("score_semantics") != "cosine_similarity_higher_is_better":
        raise ValueError("score_semantics 与当前 pgvector 检索实现不一致")


def validate_corpus(
    dataset: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], Path]:
    corpus = require_mapping(dataset.get("corpus"), "corpus")
    manifest_path = resolve_project_path(
        corpus.get("manifest_path"),
        "corpus.manifest_path",
    )
    pdf_directory = resolve_project_path(
        corpus.get("pdf_directory"),
        "corpus.pdf_directory",
    )
    manifest = read_json(manifest_path)

    corpus_version = require_non_empty_string(
        corpus.get("corpus_version"),
        "corpus.corpus_version",
    )
    if corpus_version != manifest.get("corpus_version"):
        raise ValueError("评测集 corpus_version 与 manifest 不一致")

    manifest_documents = require_list(
        manifest.get("documents"),
        "manifest.documents",
    )
    manifest_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(manifest_documents, start=1):
        document = require_mapping(item, f"manifest.documents[{index}]")
        filename = require_non_empty_string(
            document.get("filename"),
            f"manifest.documents[{index}].filename",
        )
        if filename in manifest_by_name:
            raise ValueError(f"manifest PDF 文件名重复：{filename}")
        manifest_by_name[filename] = document

    frozen_documents = require_list(
        corpus.get("documents"),
        "corpus.documents",
    )
    frozen_by_name: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(frozen_documents, start=1):
        document = require_mapping(item, f"corpus.documents[{index}]")
        filename = require_non_empty_string(
            document.get("filename"),
            f"corpus.documents[{index}].filename",
        )
        sha256 = require_non_empty_string(
            document.get("sha256"),
            f"corpus.documents[{index}].sha256",
        )
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"{filename} 的 sha256 格式错误")
        if filename in frozen_by_name:
            raise ValueError(f"评测集 PDF 文件名重复：{filename}")
        frozen_by_name[filename] = document

    expected_document_count = corpus.get("document_count")
    if type(expected_document_count) is not int:
        raise ValueError("corpus.document_count 必须是整数")
    if expected_document_count != len(frozen_by_name):
        raise ValueError("corpus.document_count 与 documents 数量不一致")
    if set(frozen_by_name) != set(manifest_by_name):
        raise ValueError("评测集冻结的 PDF 清单与 manifest 不一致")

    for filename, frozen_document in frozen_by_name.items():
        manifest_document = manifest_by_name[filename]
        frozen_hash = frozen_document["sha256"]
        if frozen_hash != manifest_document.get("sha256"):
            raise ValueError(f"{filename} 的冻结哈希与 manifest 不一致")
        pdf_path = pdf_directory / filename
        if not pdf_path.is_file():
            raise FileNotFoundError(f"缺少冻结 PDF：{pdf_path}")
        if sha256_file(pdf_path) != frozen_hash:
            raise ValueError(f"{filename} 的实际 SHA-256 已变化")

    if manifest.get("document_count") != len(manifest_by_name):
        raise ValueError("manifest.document_count 与 documents 数量不一致")

    return manifest, manifest_by_name, pdf_directory


def validate_cases(
    dataset: dict[str, Any],
    evaluation: dict[str, Any],
    manifest: dict[str, Any],
    manifest_by_name: dict[str, dict[str, Any]],
    pdf_directory: Path,
) -> Counter[str]:
    cases = require_list(dataset.get("cases"), "cases")
    if not cases:
        raise ValueError("cases 不能为空")

    readers: dict[str, PdfReader] = {}
    seen_ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    answerable_count = 0
    unanswerable_count = 0
    answerable_categories: set[str] = set()
    reserved_absent_topics = set(
        require_list(
            manifest.get("reserved_absent_topics"),
            "manifest.reserved_absent_topics",
        )
    )

    for position, item in enumerate(cases, start=1):
        case = require_mapping(item, f"cases[{position}]")
        case_id = require_non_empty_string(
            case.get("id"),
            f"cases[{position}].id",
        )
        if case_id in seen_ids:
            raise ValueError(f"case id 重复：{case_id}")
        seen_ids.add(case_id)

        category = require_non_empty_string(
            case.get("category"),
            f"{case_id}.category",
        )
        if category not in ALLOWED_CATEGORIES:
            raise ValueError(f"{case_id} 使用未知 category：{category}")
        category_counts[category] += 1

        require_non_empty_string(case.get("question"), f"{case_id}.question")
        require_non_empty_string(
            case.get("expected_answer"),
            f"{case_id}.expected_answer",
        )
        expected_points = require_list(
            case.get("expected_points"),
            f"{case_id}.expected_points",
        )
        if not expected_points:
            raise ValueError(f"{case_id}.expected_points 不能为空")
        for point_index, point in enumerate(expected_points, start=1):
            require_non_empty_string(
                point,
                f"{case_id}.expected_points[{point_index}]",
            )

        answerable = case.get("answerable")
        expected_refusal = case.get("expected_refusal")
        if type(answerable) is not bool:
            raise ValueError(f"{case_id}.answerable 必须是布尔值")
        if type(expected_refusal) is not bool:
            raise ValueError(f"{case_id}.expected_refusal 必须是布尔值")
        evidence_items = require_list(
            case.get("expected_evidence"),
            f"{case_id}.expected_evidence",
        )

        if answerable:
            answerable_count += 1
            answerable_categories.add(category)
            if category == "unanswerable":
                raise ValueError(f"{case_id} 可回答但 category 是 unanswerable")
            if expected_refusal:
                raise ValueError(f"{case_id} 可回答但 expected_refusal=true")
            if not evidence_items:
                raise ValueError(f"{case_id} 可回答但没有 expected_evidence")

            evidence_filenames: set[str] = set()
            for evidence_index, evidence_item in enumerate(
                evidence_items,
                start=1,
            ):
                evidence = require_mapping(
                    evidence_item,
                    f"{case_id}.expected_evidence[{evidence_index}]",
                )
                filename = require_non_empty_string(
                    evidence.get("filename"),
                    f"{case_id}.expected_evidence[{evidence_index}].filename",
                )
                if filename not in manifest_by_name:
                    raise ValueError(f"{case_id} 引用了未知 PDF：{filename}")
                evidence_filenames.add(filename)

                page_number = evidence.get("page_number")
                page_count = manifest_by_name[filename].get("page_count")
                if (
                    type(page_number) is not int
                    or type(page_count) is not int
                    or not 1 <= page_number <= page_count
                ):
                    raise ValueError(
                        f"{case_id} 的 {filename} 页码超出冻结范围"
                    )

                evidence_contains = require_non_empty_string(
                    evidence.get("evidence_contains"),
                    f"{case_id}.expected_evidence[{evidence_index}].evidence_contains",
                )
                if filename not in readers:
                    readers[filename] = PdfReader(pdf_directory / filename)
                extracted_text = (
                    readers[filename].pages[page_number - 1].extract_text()
                    or ""
                )
                if normalize_text(evidence_contains) not in normalize_text(
                    extracted_text
                ):
                    raise ValueError(
                        f"{case_id} 的证据原文不在 {filename} 第 {page_number} 页"
                    )

            if category == "cross_document" and len(evidence_filenames) < 2:
                raise ValueError(f"{case_id} 是跨文档题但证据不足两个 PDF")
        else:
            unanswerable_count += 1
            if category != "unanswerable":
                raise ValueError(f"{case_id} 不可回答但 category 不是 unanswerable")
            if not expected_refusal:
                raise ValueError(f"{case_id} 不可回答但 expected_refusal=false")
            if evidence_items:
                raise ValueError(f"{case_id} 不可回答但仍标注了证据")
            absent_topic = require_non_empty_string(
                case.get("absent_topic"),
                f"{case_id}.absent_topic",
            )
            if absent_topic not in reserved_absent_topics:
                raise ValueError(
                    f"{case_id}.absent_topic 不在 manifest 的保留缺失主题中"
                )

    answerable_minimum = evaluation.get("answerable_minimum")
    unanswerable_minimum = evaluation.get("unanswerable_minimum")
    if type(answerable_minimum) is not int or answerable_minimum < 12:
        raise ValueError("answerable_minimum 必须至少为 12")
    if type(unanswerable_minimum) is not int or unanswerable_minimum < 6:
        raise ValueError("unanswerable_minimum 必须至少为 6")
    if answerable_count < answerable_minimum:
        raise ValueError(
            f"可回答题不足：需要 {answerable_minimum}，实际 {answerable_count}"
        )
    if unanswerable_count < unanswerable_minimum:
        raise ValueError(
            f"无答案题不足：需要 {unanswerable_minimum}，实际 {unanswerable_count}"
        )

    required_categories = set(
        require_list(
            evaluation.get("required_answerable_categories"),
            "evaluation.required_answerable_categories",
        )
    )
    missing_categories = required_categories - answerable_categories
    if missing_categories:
        raise ValueError(
            "可回答题缺少类别：" + ", ".join(sorted(missing_categories))
        )

    return category_counts


def validate_dataset(dataset_path: Path) -> None:
    dataset = read_json(dataset_path.resolve())
    if dataset.get("schema_version") != 1:
        raise ValueError("schema_version 必须为 1")
    dataset_version = require_non_empty_string(
        dataset.get("dataset_version"),
        "dataset_version",
    )
    evaluation = require_mapping(dataset.get("evaluation"), "evaluation")
    validate_candidates(evaluation)
    manifest, manifest_by_name, pdf_directory = validate_corpus(dataset)
    category_counts = validate_cases(
        dataset=dataset,
        evaluation=evaluation,
        manifest=manifest,
        manifest_by_name=manifest_by_name,
        pdf_directory=pdf_directory,
    )

    total = sum(category_counts.values())
    answerable = total - category_counts["unanswerable"]
    print(f"OK：评测集版本 {dataset_version}")
    print(
        "OK：语料版本 "
        f"{manifest['corpus_version']}，{len(manifest_by_name)} 个 PDF 哈希一致"
    )
    print(
        f"OK：共 {total} 题（可回答 {answerable}，"
        f"无答案 {category_counts['unanswerable']}）"
    )
    print(
        "OK：题型 "
        + "，".join(
            f"{category}={category_counts[category]}"
            for category in sorted(category_counts)
        )
    )
    print("OK：JSON 结构、证据页、原文锚点和拒答标签通过校验")


def main() -> None:
    args = parse_args()
    validate_dataset(args.dataset)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError, PdfReadError) as exc:
        print(f"ERROR：{exc}", file=sys.stderr)
        raise SystemExit(1) from None
```

**这段代码怎样工作**

- 输入：新评测 JSON、它声明的 manifest 和 PDF 目录。
- 输出：确定性的版本、哈希、题目计数、类别计数和标签校验摘要；不生成模型回答或实验指标。
- 调用谁：标准库 `json`、`hashlib`、`pathlib` 和项目已固定的 `pypdf==6.15.0`。
- 被谁调用：开发者在 Day 10 手工运行；也可在 Day 11 评测前作为预检。
- 正常路径：先验证参数候选和语料哈希，再逐题检查字段、类别、答案/拒答一致性，最后从指定 PDF 页提取文本核对证据锚点。
- 失败路径：任一结构、哈希、计数、页码、原文或标签不一致时，只输出安全错误原因并以退出码 1 结束。
- 数据安全：脚本不读取 `.env`、数据库 URL、API Key 或网络资源。

**完成本步骤后的预期状态**

- `python scripts/validate_enterprise_questions.py` 可以离线运行。
- 脚本不会写入 PDF、manifest、数据库或评测结果。
- Day 11 在开始实验前可以先用同一命令确认输入没有漂移。

### 步骤 3：人工复核题目边界（建议 5 分钟）

**目标**

在不运行参数实验的前提下，确认题目表达没有把答案直接塞进问题，也没有把无答案题误标为可回答。

**修改位置**

- 文件：`data/evaluation/enterprise_questions.json`
- 定位：搜索每个 `category` 和 `absent_topic`
- 操作：只在发现标签与原始 PDF 明确冲突时修正；不要根据模型试答结果改题

**复制下面的完整检查命令**

```powershell
python scripts/validate_enterprise_questions.py
Select-String -Path 'data/evaluation/enterprise_questions.json' `
    -Pattern '"category":|"absent_topic":|"evidence_contains":'
```

**这段检查怎样工作**

- 输入：已经创建的固定评测集。
- 输出：自动校验摘要和供人工快速浏览的类别、无答案主题、证据锚点。
- 调用谁：Day 10 校验脚本和 PowerShell `Select-String`。
- 被谁调用：今天执行计划的开发者。
- 正常路径：所有题都能追溯到冻结语料或保留缺失主题。
- 失败路径：发现题意含糊时回到对应 PDF 原文复核，不使用 LLM 回答作为标签依据。

**完成本步骤后的预期状态**

- 12 道可回答题能由标注证据独立回答。
- 6 道无答案题均落在 manifest 明确保留的缺失主题内。
- 数据集版本、语料版本和 PDF 哈希形成同一个冻结边界。

## 六、运行数据库迁移或环境命令

> 今天不涉及数据库结构变更，不生成或执行 Alembic migration；核心数据集校验可离线完成，数据库与 API 只用于后面的可选运行态对齐检查。

### 1. 检查当前状态

执行目录：项目根目录。先确认依赖、Git 边界和 Day 9 冻结语料；这些命令只读，不会重建 PDF。

```powershell
git status --short
python --version
python -c "import pypdf; print('pypdf', pypdf.__version__)"
python scripts/generate_demo_pdfs.py --verify-only
```

预期结果：

- 开始修改前 `git status --short` 没有输出；如果出现文件，先辨认并保护用户已有修改。
- Python 能导入仓库固定的 `pypdf`；当前 `requirements.txt` 固定版本为 `6.15.0`。
- `--verify-only` 输出 4 行 `OK`、语料版本 `2026-09-04-v1` 和 manifest 路径。
- 如果缺少依赖，在确认当前虚拟环境后执行 `python -m pip install -r requirements.txt`；安装时间不计入核心学习时间。

### 2. 执行升级

按第五部分新建两个文件后执行：

```powershell
python scripts/validate_enterprise_questions.py
```

执行顺序：必须先保存完整 JSON，再保存完整校验脚本，最后运行命令。

### 3. 回滚并恢复

今天没有数据库迁移，因此没有 `alembic downgrade` 或结构恢复步骤；也不要删除 PostgreSQL Volume。若新文件尚未提交且需要放弃本次练习，只手工核对并处理当天两个明确新文件，不使用批量删除或破坏性 Git 命令。

### 预期结果

- 命令退出码为 `0`。
- 输出评测集版本与语料版本均为 `2026-09-04-v1`。
- 输出 4 个 PDF 哈希一致。
- 输出共 18 题，其中可回答 12、无答案 6。
- 输出所有题型计数，并确认 JSON 结构、证据页、原文锚点和拒答标签通过校验。
- 这些都是预期结果；没有实际执行前不能写成已经通过。

## 七、验证正常路径

### 启动或准备服务

核心正常路径是离线验证，不需要启动数据库或 API：

```powershell
python scripts/generate_demo_pdfs.py --verify-only
python scripts/validate_enterprise_questions.py
```

如需同时核对运行态的 Document/Chunk 动态 ID，可选执行下面步骤。先启动 PostgreSQL、迁移和 API；Uvicorn 命令在第二个 PowerShell 窗口保持运行，按 `Ctrl+C` 退出：

```powershell
docker compose up -d postgres
docker compose ps
alembic upgrade head
python -m uvicorn app.main:app --reload
```

然后在另一个项目根目录 PowerShell 窗口中，创建一个唯一命名的临时评测知识库并上传 4 份冻结 PDF；首次下载 Embedding 模型的时间不计入核心学习时间：

```powershell
$apiBase = 'http://127.0.0.1:8000'

# 创建唯一知识库
$knowledgeBaseName = 'Day10固定评测-' + (Get-Date -Format 'yyyyMMdd-HHmmss')

$knowledgeBaseBody = @{
    name = $knowledgeBaseName
    description = 'Day 10 固定评测集运行态对齐'
} | ConvertTo-Json


$knowledgeBase = Invoke-RestMethod `
    -Method Post `
    -Uri "$apiBase/knowledge-bases" `
    -ContentType 'application/json; charset=utf-8' `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($knowledgeBaseBody))


$knowledgeBaseId = $knowledgeBase.id

Write-Host "Created knowledge base id=$knowledgeBaseId"


# 上传 PDF
Get-ChildItem -LiteralPath 'data/demo_policies/pdfs' -Filter '*.pdf' |
    Sort-Object Name |
    ForEach-Object {

        Write-Host "Uploading $($_.Name)"

        curl.exe `
            -X POST `
            "$apiBase/knowledge-bases/$knowledgeBaseId/documents" `
            -F "file=@$($_.FullName)"
    }


# 查询上传结果

Invoke-RestMethod `
    -Method Get `
    -Uri "$apiBase/knowledge-bases/$knowledgeBaseId/documents" |
    ConvertTo-Json -Depth 5
```

### 执行正常请求或测试

先执行固定输入的完整离线校验：

```powershell
python scripts/validate_enterprise_questions.py
```

可选：在刚才上传完成的同一 PowerShell 会话中，用 API 返回确认 4 份文档都是 `ready`；再用下面只读数据库查询查看动态 ID 和 Chunk 数量。命令通过 `app.db.SessionLocal` 使用现有配置，不打印数据库密码：

```powershell
@'
from sqlalchemy import func, select

from app.db import SessionLocal
from app.orm_models import Chunk, Document

filenames = (
    "员工请假与考勤制度.pdf",
    "差旅与费用报销制度.pdf",
    "采购与办公资产管理制度.pdf",
    "访客与会议室管理办法.pdf",
)

statement = (
    select(
        Document.id,
        Document.filename,
        Document.status,
        func.count(Chunk.id).label("chunk_count"),
    )
    .outerjoin(Chunk, Chunk.document_id == Document.id)
    .where(Document.filename.in_(filenames))
    .group_by(Document.id, Document.filename, Document.status)
    .order_by(Document.filename, Document.id)
)

with SessionLocal() as session:
    rows = session.execute(statement).all()
    for document_id, filename, status, chunk_count in rows:
        print(document_id, filename, status, chunk_count)
'@ | python -
```

### 预期状态码或输出结构

离线校验预期输出结构：

```text
OK：评测集版本 2026-09-04-v1
OK：语料版本 2026-09-04-v1，4 个 PDF 哈希一致
OK：共 18 题（可回答 12，无答案 6）
OK：题型 comprehensive=3，cross_document=2，direct_fact=4，isolation=3，unanswerable=6
OK：JSON 结构、证据页、原文锚点和拒答标签通过校验
```

可选上传接口每次预期 HTTP `201`，稳定响应结构如下；所有 ID、时间和 Chunk 数量都是动态值：

```json
{
  "document": {
    "id": "动态正整数",
    "knowledge_base_id": "动态正整数",
    "filename": "当前上传的 PDF 文件名",
    "status": "ready",
    "failure_reason": null,
    "created_at": "动态时间",
    "updated_at": "动态时间"
  },
  "page_count": 2,
  "chunk_count": "动态正整数"
}
```

### 为什么它能证明今天已经完成

- manifest 校验先证明题目绑定的确实是 Day 9 冻结字节，而不是同名但内容变化的 PDF。
- 逐页提取校验证明每个可回答题的 Ground truth 原文真实存在于标注文件和页码。
- 数量、类别和拒答标签校验证明数据集满足 Day 10 的覆盖要求。
- 可选 HTTP 与数据库查询只负责把稳定的文件名/页码标签对齐到当前运行产生的 Document/Chunk 动态 ID；实际执行和记录不作为进入 Day 11 的前提。

## 八、验证失败和边界路径

### 场景：证据锚点被错误修改，校验器必须拒绝数据集

执行目录：项目根目录。下面只创建一个明确的失败测试副本，不修改正式数据集；最后只删除这个明确路径的副本。

```powershell
Copy-Item `
    -LiteralPath 'data/evaluation/enterprise_questions.json' `
    -Destination 'data/evaluation/enterprise_questions.invalid.json'

$invalidDataset = Get-Content `
    -LiteralPath 'data/evaluation/enterprise_questions.invalid.json' `
    -Raw |
    ConvertFrom-Json
$invalidDataset.cases[0].expected_evidence[0].evidence_contains = `
    '这段故意构造的证据不在任何冻结 PDF 中'
$invalidDataset |
    ConvertTo-Json -Depth 20 |
    Set-Content `
        -LiteralPath 'data/evaluation/enterprise_questions.invalid.json' `
        -Encoding utf8

python scripts/validate_enterprise_questions.py `
    --dataset data/evaluation/enterprise_questions.invalid.json
$LASTEXITCODE

Remove-Item `
    -LiteralPath 'data/evaluation/enterprise_questions.invalid.json'
```

### 预期结果

- HTTP 状态码或异常：该场景不调用 HTTP；脚本输出 `ERROR：direct-leave-01 的证据原文不在 员工请假与考勤制度.pdf 第 1 页`，进程退出码为 `1`。
- 数据库应该保留：全部现有 KnowledgeBase、Document、Chunk 和向量原样保留；脚本不连接数据库。
- 数据库不应该存在：不应因校验失败产生任何新数据库记录。
- 文件系统应该保留：正式 `enterprise_questions.json`、4 份 PDF 和 manifest 内容不变；测试结束后仅失败副本被删除。
- 响应不能泄露：错误中不能出现 `.env` 内容、数据库密码、API Key、连接串、Embedding 向量或内部堆栈。
- 如果正式校验也失败，不要把失败写成已通过；按错误中的 case ID、文件名和页码回查标注。

## 九、常见错误与解决办法

| 错误现象 | 最可能原因 | 检查命令或位置 | 解决方法 |
| --- | --- | --- | --- |
| `ModuleNotFoundError: No module named 'pypdf'` | 当前 PowerShell 没有进入项目虚拟环境或依赖未安装 | `python -c "import sys; print(sys.executable)"` 和 `requirements.txt` | 激活项目虚拟环境后执行 `python -m pip install -r requirements.txt`，再重跑校验 |
| `评测集 corpus_version 与 manifest 不一致` | 复制了旧版本号，或 Day 9 语料已正式升级但数据集未同步升级 | 对比 `enterprise_questions.json` 的 `corpus.corpus_version` 与 `manifest.json` | 先确认是否真的要升级冻结语料；若是，使用新版本号和新哈希完整重标，不能只改一个字符串绕过校验 |
| `实际 SHA-256 已变化` | PDF 被重新生成、手工编辑或损坏 | `Get-FileHash -Algorithm SHA256 -LiteralPath '具体 PDF 路径'` | 运行 `python scripts/generate_demo_pdfs.py --verify-only` 定位漂移；不要把新哈希直接抄进数据集掩盖未知变化 |
| `证据原文不在某 PDF 第 N 页` | 页码标错、锚点不是原文、中文标点不同，或 PDF 已漂移 | 打开 `data/demo_policies/policies.yaml` 对应 page，并用 `python scripts/generate_demo_pdfs.py --verify-only` | 把 `evidence_contains` 改为该页真实、足够区分的短原文；不能改成模型生成的概括句 |
| `可回答题缺少类别` | 删除或误改了 direct/comprehensive/cross_document/isolation 标签 | `Select-String -Path 'data/evaluation/enterprise_questions.json' -Pattern '"category":'` | 恢复四类题型覆盖；跨文档题必须至少引用两个不同 PDF |
| `不可回答但 expected_refusal=false` | `answerable`、`expected_refusal` 和 `category` 三个字段互相矛盾 | 搜索错误中给出的 case ID | 无答案题统一使用 `answerable=false`、`category=unanswerable`、`expected_refusal=true` 和空证据数组 |
| 失败副本被 PowerShell 写坏或 JSON 深层字段丢失 | `ConvertTo-Json` 深度不足或编码参数遗漏 | `Get-Content -LiteralPath 'data/evaluation/enterprise_questions.invalid.json' -Raw` | 使用计划中的 `ConvertTo-Json -Depth 20` 和 `Set-Content -Encoding utf8`，测试后只删除该明确副本 |
| 上传 PDF 返回 `400` | 文件路径、扩展名、文件内容或表单字段不正确 | 检查 `data/demo_policies/pdfs` 和请求中的 `file` 字段 | 先运行 Day 9 `--verify-only`，再用 PowerShell 7 的 `Invoke-RestMethod -Form @{ file = $_ }` |
| 上传 PDF 返回 `500` 或 API 返回 `503` | Embedding、数据库或 LLM 环境未就绪；不是固定标签本身失败 | 查看 Uvicorn 日志、`docker compose ps`、`python scripts/validate_enterprise_questions.py` | 把离线数据校验和运行环境问题分开处理；错误响应不得回显真实密码或 API Key |

## 十、检查最终代码差异

执行目录：项目根目录。新文件未暂存时 `git diff` 可能不显示正文，所以同时检查状态、完整文件和校验输出：

```powershell
git status --short
git diff -- `
    data/evaluation/enterprise_questions.json `
    scripts/validate_enterprise_questions.py `
    docs/17天每日学习/Day10.md
Get-Content -LiteralPath 'data/evaluation/enterprise_questions.json' -Raw
Get-Content -LiteralPath 'scripts/validate_enterprise_questions.py' -Raw
python scripts/validate_enterprise_questions.py
```

重点检查：

- 当天只有一套企业制度固定评测集，旧单 PDF 基线文件没有被修改。
- `dataset_version`、`corpus_version`、4 个文件名和 SHA-256 与 manifest 一致。
- 12 道可回答题都有答案要点和至少一个真实页级证据；2 道跨文档题各引用至少两个 PDF。
- 6 道无答案题都有明确拒答标签、空证据数组和 manifest 中的保留缺失主题。
- JSON 中没有 `model_answer`、实时相似度、延迟、实际 Chunk ID 或手工填入的运行结论。
- 校验脚本只读固定数据，不读取秘密、不访问网络、不写数据库。
- `git status` 不包含 `.env`、数据库文件、缓存、失败测试副本或无关修改。

## 十一、Git 提交

核心实现完成并检查 Git diff 边界后即可执行；不要求提供 API、数据库或 Day 11 指标结果。如果离线校验存在已知失败，应先修复再提交。

```powershell
git add `
    data/evaluation/enterprise_questions.json `
    scripts/validate_enterprise_questions.py `
    docs/17天每日学习/Day10.md

git diff --cached --stat
git diff --cached -- `
    data/evaluation/enterprise_questions.json `
    scripts/validate_enterprise_questions.py `
    docs/17天每日学习/Day10.md
git status --short
git commit -m "Day10 add fixed enterprise RAG evaluation dataset"
```

提交前确认暂存区只有这三个明确文件，不使用 `git add .`，不提交失败测试副本、真实秘密或运行时数据库文件。

## 十二、面试高频问题与参考答案

### 问题 1：Ground truth 为什么不能直接用模型回答？

#### 30 秒参考答案

Ground truth 是评测前人工冻结的正确标准，模型回答是被评估对象；如果用模型输出反过来当标准，错误会自我证明。在这个项目中，我把正确答案拆成 `expected_points` 和 `expected_evidence`，证据绑定 Day 9 冻结 PDF 的文件名、页码和原文，Day 11 的 `model_answer`、来源和分数则写到单独结果文件中。

#### 继续追问：答案措辞必须与 expected_answer 完全相同吗？

不必。企业 RAG 的回答可以有不同措辞，所以 `expected_answer` 主要帮助人工理解，真正稳定的判断依据是关键答案点是否覆盖、正确证据是否命中、是否引用错误来源，以及无答案题是否正确拒答。后续脚本可以分别记录这些维度，不能只做字符串全等。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的 `expected_points`、`expected_evidence`、`expected_refusal`
- `app/models.py` 的 `KnowledgeBaseQueryResponse` 和 `KnowledgeBaseQuerySource`

### 问题 2：为什么 Ground truth 不直接保存数据库的 chunk_id？

#### 30 秒参考答案

当前 `Chunk.id` 是数据库自增主键，同一 PDF 在不同环境或重新上传后会得到不同 ID，把它写死会让数据集无法复现。我使用 manifest 固定 PDF SHA-256，再用文件名、物理页码和原文锚点标注稳定证据；运行评测时仍保留实际 `chunk_id` 和 `document_id`，用于定位当次检索结果。

#### 继续追问：如果 Chunk 切分参数变化怎么办？

页码和原文锚点仍能判断正确事实是否出现在返回 Chunk 中，但排名可能变化，这正是实验要测的内容。如果语料字节或标注事实本身变化，就必须升级 corpus 和 dataset 版本并重新核对标签，不能只替换哈希继续沿用旧结论。

#### 回答时要引用的项目依据

- `data/demo_policies/manifest.json` 的 `corpus_version` 与 `sha256`
- `data/evaluation/enterprise_questions.json` 的 `expected_evidence`
- `app/orm_models.py` 的 `Chunk.id`、`page_number`、`chunk_index` 和 `content`

### 问题 3：如何避免为了获得更高指标而污染评测集？

#### 30 秒参考答案

我先冻结语料版本、PDF 哈希、18 道题、答案要点和证据标签，再进行 Day 11 的参数实验。Top-K 和阈值候选也提前写入数据集；如果某个参数表现差，只能记录结果和分析原因，不能回头改题。旧单 PDF 基线与新企业评测集使用不同文件，避免历史结果混入新结论。

#### 继续追问：开发时发现题目确实标错怎么办？

如果能从冻结 PDF 证明标签错误，可以修正，但要升级数据集版本、记录变更原因，并让所有参数重新跑同一新版数据集；不能只修正对某个参数不利的个别结果后继续比较旧报告。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的 `dataset_version` 和参数候选
- `scripts/validate_enterprise_questions.py` 的语料哈希与证据页校验
- `data/evaluation/questions.json` 仍保留为旧单 PDF 基线

### 问题 4：为什么评测集必须同时包含可回答题和无答案题？

#### 30 秒参考答案

只测可回答题会鼓励系统对所有问题都强行给答案，无法衡量幻觉风险。当前数据集有 12 道可回答题验证证据召回和答案要点，也有 6 道来自 manifest 保留缺失主题的无答案题，验证 `DatabaseRAGService` 在证据不足时是否返回 `refused=true`、固定拒答文本和空来源。

#### 继续追问：向量数据库总会返回 Top-K，怎么判断应该拒答？

Top-K 只是相对最接近的候选，不代表绝对可靠。当前实现用 cosine similarity 和参考阈值 `0.55` 过滤候选；过滤后没有可靠 Chunk 才拒答。Day 11 会比较预先固定的阈值候选，联合观察 Recall、MRR 与拒答正确率，而不是只追求召回率。

#### 回答时要引用的项目依据

- `app/services/database_rag_service.py` 的 `MIN_RELEVANCE_SCORE`、`REFUSAL_ANSWER` 和空来源返回
- `data/demo_policies/manifest.json` 的 `reserved_absent_topics`
- `data/evaluation/enterprise_questions.json` 的 6 个 `unanswerable` case

### 问题 5：这套评测集如何覆盖企业 RAG 的不同错误模式？

#### 30 秒参考答案

我把可回答题分成四类：直接事实检查单证据召回，综合题检查同一制度多个要点，跨文档题检查两个制度能否共同被检索，隔离题检查相近金额、期限和流程不会串线；无答案题再检查拒答。这样能把“召回不到”“召回不全”“串到相似规则”和“无证据仍生成”区分开。

#### 继续追问：当前评测集有什么限制？

它只有 18 题和 4 份两页的合成制度，适合验证数据流和做小规模参数对照，不代表生产规模效果；答案要点仍包含人工判断，尚未覆盖 OCR、复杂表格、多模态、权限隔离或大规模并发。这些限制不能在简历中夸大。

#### 回答时要引用的项目依据

- `data/evaluation/enterprise_questions.json` 的题型分布与 18 个 case
- `data/demo_policies/README.md` 的语料范围与明确排除项
- `docs/17天-当前项目每日安排.md` 的本轮范围

## 十三、今天的完整数据流

### 正常路径

```text
Day 9 policies.yaml
→ 生成 4 份文本型 PDF
→ manifest.json 冻结 corpus_version、页数和 SHA-256
→ enterprise_questions.json 冻结题目、答案要点、证据与拒答标签
→ validate_enterprise_questions.py 读取 JSON
→ 对比 manifest 版本、文件清单和 PDF 实际哈希
→ 从标注页提取文本并核对 evidence_contains
→ 检查 12 道可回答题、6 道无答案题和全部题型
→ 退出码 0
→ Day 11 只读取固定输入并把运行结果另存
```

可选运行态对齐：

```text
4 份冻结 PDF
→ 上传到同一个 KnowledgeBase
→ DocumentIngestionService 生成动态 Document/Chunk ID
→ API 列表和只读数据库查询核对 filename、status、Chunk 数量
→ Day 11 结果保留当次 ID、页码、原文和分数
→ 固定 Ground truth 本身不写死动态 ID
```

### 失败路径

```text
JSON 字段缺失 / 数量不足 / 标签矛盾
或 corpus_version、PDF 哈希、页码、证据原文不一致
→ 校验器定位 dataset 字段或 case ID
→ stderr 输出安全错误摘要
→ 退出码 1
→ 不连接数据库、不调用 LLM、不生成评测结果
→ 修正可复现的标签错误后重新校验
→ 已知失败未解决前不提交
```

## 十四、完成标准

```text
[ ] 能解释 Ground truth、模型回答和检索来源为什么必须分开保存
[ ] 能解释为什么固定证据使用 PDF 哈希 + 文件名 + 页码 + 原文锚点，而不写死自增 Chunk ID
[ ] 已新建 data/evaluation/enterprise_questions.json，且没有覆盖旧 questions.json
[ ] 数据集包含 12 道可回答题和 6 道无答案题，并覆盖直接事实、综合、跨文档和隔离场景
[ ] 每道可回答题都有 expected_points 和可从冻结 PDF 指定页找到的 expected_evidence
[ ] 每道无答案题都使用 manifest 保留缺失主题、expected_refusal=true 和空证据数组
[ ] 已提供可执行的正常路径校验命令与预期退出码 0；实际执行和记录可选
[ ] 已提供证据锚点损坏的失败路径命令与预期退出码 1；实际执行和记录可选
[ ] 能不看代码复述“冻结语料 → 固定标签 → 离线校验 → Day 11 运行结果”的完整数据流
[ ] git diff 和暂存区只包含企业评测 JSON、校验脚本和 Day10 手册，不包含秘密、运行结果或无关修改
[ ] 核心实现完成并检查 diff 后，可以执行边界清晰的 Day 10 Git commit
```

## 十五、可选执行记录

- 实际完成：已完成
- 验证结果：可选，不要求填写
- 用户完成标记：完成
- 遇到的错误：暂无
- 最终解决方式：暂无
- Git commit：已提交
