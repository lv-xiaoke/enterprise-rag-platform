# Day 22：运行 RAG 基线评估并保存结果

昨天已经建立了 `data/evaluation/questions.json`，里面有 12 个固定问题、标准答案和关键得分点。这个 JSON 只是“题库和答案册”，本身不会调用程序。今天要创建一个评估运行脚本：自动上传 `sample.pdf`，逐题调用 `/rag/chat`，把模型回答和检索来源保存到独立的 `baseline_results.json`，然后由你人工填写检索是否命中、回答是否正确。完成后，项目会得到第一份可以用于后续参数对比的 RAG 基线结果。

---

# 一、先理解题库、运行脚本和结果文件的关系

打开项目并激活虚拟环境：

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
```

今天涉及三个不同角色的文件：

```text
questions.json
→ 保存固定问题、标准答案和关键得分点

run_evaluation.py
→ 读取题库、调用接口、收集实际输出

baseline_results.json
→ 保存本次运行得到的 sources、answer 和人工评分
```

整个过程是：

```text
读取 question
→ 上传测试 PDF
→ 调用 POST /rag/chat
→ 获得 sources 和 answer
→ 保存实际输出
→ 人工对照 expected_answer 评分
```

需要特别注意：评估脚本发给接口的请求体只有：

```json
{
  "question": "问题内容"
}
```

下面这些内容不能发送给 RAG：

```text
expected_answer
expected_points
answerable
```

否则相当于考试时把标准答案也交给了考生，评估结果就失去意义。

---

# 二、为什么不直接覆盖 questions.json

今天把运行结果写入：

```text
data/evaluation/baseline_results.json
```

而不是覆盖：

```text
data/evaluation/questions.json
```

因为两者职责不同：

```text
questions.json
→ 固定测试集，相当于不会随实验改变的试卷

baseline_results.json
→ 当前参数下的一次答卷
```

以后如果把 `top_k` 从 3 改成 5，可以生成另一个结果文件，再与基线比较。固定题库不变，才能判断差异来自参数变化，而不是题目发生了变化。

当前基线参数已经记录在题库中：

```json
{
  "chunk_size": 200,
  "overlap": 40,
  "top_k": 3
}
```

它们与 `app/main.py` 当前的三个常量一致。今天不要修改这些参数，先测出原始效果。

---

# 三、创建评估运行脚本

创建脚本目录：

```powershell
New-Item -ItemType Directory -Force scripts
```

新建：

```text
scripts/run_evaluation.py
```

写入：

```python
import json
from pathlib import Path

import httpx


BASE_URL = "http://127.0.0.1:8000"
QUESTIONS_PATH = Path("data/evaluation/questions.json")
RESULTS_PATH = Path(
    "data/evaluation/baseline_results.json"
)

# 第一次只运行 1 道题。
# 单题成功后改为 None，表示运行全部问题。
CASE_LIMIT: int | None = 1


def save_results(data: dict) -> None:
    """将当前进度保存为便于人工阅读的 JSON。"""
    RESULTS_PATH.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    data = json.loads(
        QUESTIONS_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    document_path = Path(data["document"])
    all_cases = data["cases"]
    selected_cases = (
        all_cases
        if CASE_LIMIT is None
        else all_cases[:CASE_LIMIT]
    )

    if not document_path.exists():
        raise FileNotFoundError(
            f"评估 PDF 不存在：{document_path}"
        )

    print("评估文档：", document_path)
    print("本次问题数：", len(selected_cases))
    print("基线参数：", data["baseline"])

    try:
        with httpx.Client(
            base_url=BASE_URL,
            timeout=120.0,
        ) as client:
            health_response = client.get("/health")
            health_response.raise_for_status()

            with document_path.open("rb") as pdf_file:
                upload_response = client.post(
                    "/upload",
                    files={
                        "file": (
                            document_path.name,
                            pdf_file,
                            "application/pdf",
                        )
                    },
                )

            upload_response.raise_for_status()
            print("上传结果：", upload_response.json())

            for position, case in enumerate(
                selected_cases,
                start=1,
            ):
                print(
                    f"\n[{position}/{len(selected_cases)}] "
                    f"{case['id']}：{case['question']}"
                )

                try:
                    response = client.post(
                        "/rag/chat",
                        json={
                            "question": case["question"]
                        },
                    )
                    response.raise_for_status()
                    result = response.json()

                    case["retrieved_sources"] = result[
                        "sources"
                    ]
                    case["model_answer"] = result["answer"]
                    case["retrieval_hit"] = None
                    case["answer_correct"] = None
                    case["notes"] = ""

                    print("模型回答：", result["answer"])
                    print(
                        "来源数量：",
                        len(result["sources"]),
                    )
                except (
                    httpx.HTTPError,
                    KeyError,
                    ValueError,
                ) as exc:
                    case["notes"] = (
                        f"运行失败：{type(exc).__name__}: "
                        f"{exc}"
                    )
                    print(case["notes"])

                # 每完成一道题就保存，避免中途失败后丢失进度。
                save_results(data)
    except httpx.RequestError as exc:
        raise RuntimeError(
            "无法连接 FastAPI，请先启动 Uvicorn"
        ) from exc
    print("\n结果已保存到：", RESULTS_PATH)


if __name__ == "__main__":
    main()
```

今天使用普通同步的 `httpx.Client`，因为评估脚本只按顺序运行一批问题，暂时不需要并发请求。顺序执行还有一个好处：终端输出与问题顺序一致，更容易发现是哪道题失败。

不要为了加速同时发出 12 个模型请求。并发会增加限流、费用和排查难度，也不是今天的学习重点。

---

# 四、理解脚本中的关键设计

## 1. `CASE_LIMIT` 为什么先设为 1

第一次运行时：

```python
CASE_LIMIT: int | None = 1
```

表示只取：

```python
all_cases[:1]
```

也就是只测试 `fact-01`。这样可以先检查：

```text
服务能否连接
PDF 能否上传
问题能否正常发送
中文回答能否显示
结果文件能否成功保存
```

如果脚本结构有错误，只会消耗一次模型调用，不会连续失败 12 次。

单题成功以后改成：

```python
CASE_LIMIT: int | None = None
```

表示运行全部问题。

## 2. 为什么脚本每次都先上传 PDF

当前 `rag_service` 只保存在 FastAPI 进程内存中：

```text
服务刚启动 → 没有索引
POST /upload → 建立索引
POST /rag/chat → 使用该索引回答
```

评估脚本自动上传 PDF，就不依赖你是否在另一个终端手动上传过，也让每次评估的准备步骤保持一致。

## 3. 为什么用 `response.raise_for_status()`

如果接口返回 400、500 或 502，不能继续把错误响应当成正常结果读取。`raise_for_status()` 会把错误状态转换成异常，再由脚本记录到：

```json
"notes": "运行失败：……"
```

## 4. 为什么每道题后都保存一次

12 次大模型调用可能花费一段时间。如果第 10 道题遇到网络错误，前 9 道已经得到的答案不应该丢失。因此脚本在每轮末尾执行：

```python
save_results(data)
```

这是一种简单的进度保护。

## 5. 为什么程序不自动填写正确或错误

不同说法可能表达相同含义，例如：

```text
文档切分后的文本片段
把长文档拆成较小文本块
```

二者含义接近，但简单字符串比较可能误判。无答案题是否真的“明确说明不知道”，也需要结合完整回答判断。

所以脚本只负责采集：

```text
retrieved_sources
model_answer
```

下面两个字段仍由人工评分：

```text
retrieval_hit
answer_correct
```

---

# 五、先运行一道题验证流程

今天需要两个终端。

## 终端 A：启动 FastAPI

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
.\.venv\Scripts\Activate.ps1
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

等到终端出现：

```text
Application startup complete
```

## 终端 B：运行评估脚本

```powershell
cd D:\my_develop\A_work_program\AI-study-2608\260804_mini-rag-backend
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
.\.venv\Scripts\python.exe scripts\run_evaluation.py
```

这里明确使用：

```text
.\.venv\Scripts\python.exe
```

不要只写 `python`。你之前虽然终端提示有 `(.venv)`，但实际 `python` 曾指向 Anaconda；使用完整虚拟环境路径可以避免解释器混淆。

单题成功时，终端应看到类似：

```text
评估文档： data\documents\sample.pdf
本次问题数： 1
上传结果： {'filename': 'sample.pdf', ...}

[1/1] fact-01：这份测试 PDF 一共有多少页？
模型回答：……
来源数量： 3

结果已保存到： data\evaluation\baseline_results.json
```

检查结果文件：

```powershell
Get-Item data\evaluation\baseline_results.json |
    Select-Object FullName, Length

code data\evaluation\baseline_results.json
```

确认 `fact-01` 中已经出现：

```json
"retrieved_sources": ["……"],
"model_answer": "……"
```

其他 11 道题仍为空是正常的，因为当前 `CASE_LIMIT=1`。

---

# 六、确认单题成功后运行全部问题

打开：

```text
scripts/run_evaluation.py
```

把：

```python
CASE_LIMIT: int | None = 1
```

改为：

```python
CASE_LIMIT: int | None = None
```

然后重新执行：

```powershell
.\.venv\Scripts\python.exe scripts\run_evaluation.py
```

脚本会从原始 `questions.json` 重新读取全部 12 道题，再覆盖 `baseline_results.json`。因此之前的单题测试结果不会混进完整基线。

这一步会调用大模型 12 次，会消耗相应 API 额度，并且可能需要几分钟。运行过程中不要重复启动第二个评估脚本。

正常情况下会依次看到：

```text
[1/12] fact-01：……
[2/12] fact-02：……
……
[12/12] unknown-02：……
```

运行结束后验证结果数量：

```powershell
$env:PYTHONIOENCODING = "utf-8"

@'
import json
from pathlib import Path


path = Path(
    "data/evaluation/baseline_results.json"
)
data = json.loads(
    path.read_text(encoding="utf-8-sig")
)
cases = data["cases"]

completed = [
    case
    for case in cases
    if case["model_answer"].strip()
]
failed = [
    case
    for case in cases
    if case["notes"].startswith("运行失败")
]

print("问题总数：", len(cases))
print("成功获得回答：", len(completed))
print("运行失败：", len(failed))

for case in failed:
    print(case["id"], case["notes"])

assert len(cases) == 12
assert len(completed) + len(failed) == 12
'@ | .\.venv\Scripts\python.exe -
```

理想输出是：

```text
问题总数： 12
成功获得回答： 12
运行失败： 0
```

如果有请求失败，不要反复覆盖结果文件。先根据 `notes` 判断是服务没有启动、上游超时还是接口错误，并把情况记录在今天的“遇到的卡点”中。

---

# 七、逐题人工评分

打开：

```powershell
code data\evaluation\baseline_results.json
```

对于 `answerable=true` 的 10 道题，按顺序检查。

## 1. 先评检索

暂时不看模型回答，对照 `expected_answer` 和 `expected_points` 阅读：

```json
"retrieved_sources"
```

如果至少有一个或多个来源合起来包含回答问题所需的关键资料，填写：

```json
"retrieval_hit": true
```

如果 top-3 中缺少关键资料，填写：

```json
"retrieval_hit": false
```

## 2. 再评回答

阅读：

```json
"model_answer"
```

如果回答覆盖必要得分点、没有明显事实错误，并且没有加入来源中缺乏依据的重要结论，填写：

```json
"answer_correct": true
```

否则填写：

```json
"answer_correct": false
```

再在 `notes` 中简要说明理由：

```json
"notes": "检索命中，但回答遗漏中文译名"
```

## 3. 两道无答案题怎么评

对于：

```text
unknown-01
unknown-02
```

不存在一个“包含正确答案的 Chunk”，所以：

```json
"retrieval_hit": null
```

保持不变，表示该指标不适用。

只判断模型是否遵守约束。如果它明确说明文档没有提供相关信息：

```json
"answer_correct": true
```

如果它编造了具体模型、作者或年份：

```json
"answer_correct": false
```

不要因为模型恰好凭自身知识答对某个事实，就把 `retrieval_hit` 标成 `true`。检索命中只看 `sources`，回答正确只看最终回答，两者必须分开。

---

# 八、计算第一版基线指标

完成 12 道题的人工评分后运行：

```powershell
$env:PYTHONIOENCODING = "utf-8"

@'
import json
from collections import defaultdict
from pathlib import Path


path = Path(
    "data/evaluation/baseline_results.json"
)
data = json.loads(
    path.read_text(encoding="utf-8-sig")
)
cases = data["cases"]

retrieval_cases = [
    case
    for case in cases
    if case["retrieval_hit"] is not None
]
answer_cases = [
    case
    for case in cases
    if case["answer_correct"] is not None
]

retrieval_hits = sum(
    case["retrieval_hit"]
    for case in retrieval_cases
)
correct_answers = sum(
    case["answer_correct"]
    for case in answer_cases
)

print(
    "检索命中率：",
    f"{retrieval_hits}/{len(retrieval_cases)}",
)
print(
    "回答正确率：",
    f"{correct_answers}/{len(answer_cases)}",
)

category_stats = defaultdict(
    lambda: {"correct": 0, "total": 0}
)

for case in answer_cases:
    stats = category_stats[case["category"]]
    stats["total"] += 1
    stats["correct"] += int(
        case["answer_correct"]
    )

print("\n按问题类型统计：")
for category, stats in category_stats.items():
    print(
        category,
        f"{stats['correct']}/{stats['total']}",
    )
'@ | .\.venv\Scripts\python.exe -
```

这里不提前给出应该达到的百分比。样本只有 12 道，当前目标是发现具体失败案例，而不是用一个漂亮数字证明系统已经成熟。

例如：

```text
检索命中率低
→ 优先检查 Chunk 和 top-k

检索命中但回答错误
→ 优先检查 Prompt 和生成阶段

无答案题编造信息
→ 检查模型是否遵守资料边界
```

今天只记录基线，不调整参数。下一次再根据失败问题有针对性地比较 `chunk_size`、`overlap` 和 `top_k`。

---

# 九、检查改动并提交 Git

完成运行与人工评分后执行：

```powershell
git status --short
git diff -- scripts/run_evaluation.py data/evaluation/baseline_results.json docs/Day22.md
```

今天正常应新增：

```text
scripts/run_evaluation.py
data/evaluation/baseline_results.json
docs/Day22.md
```

确认：

```text
questions.json 仍然是固定题库，没有被运行结果覆盖
app/main.py 中的三个基线参数没有修改
没有修改 RAG、Embedding 或 FAISS 业务逻辑
baseline_results.json 不包含 API Key 或 .env 内容
失败问题的评分理由已经写入 notes
```

脚本和结果文件中只包含测试问题、PDF 原文片段和模型回答，可以进入本次学习提交。测试完成后执行：

```powershell
git add scripts/run_evaluation.py data/evaluation/baseline_results.json docs/Day22.md
git status
```

确认暂存区只有今天的脚本、结果和学习记录，再提交：

```powershell
git commit -m "test: run RAG baseline evaluation"
```

最后查看：

```powershell
git log -1 --oneline
git status --short
```

尝试不看代码说明：`questions.json`、评估脚本和结果文件分别负责什么，为什么标准答案不能发送给 RAG，为什么先运行一道题再运行全部问题，以及检索命中率和回答正确率为什么要分别计算。

---

# Day 22 完成标准

- [ ] 能解释题库、评估运行脚本和基线结果文件的职责区别
- [ ] 已创建 `scripts/run_evaluation.py`
- [ ] 脚本会读取 `questions.json`，但只把 `question` 发送给 RAG 接口
- [ ] 脚本会自动上传 `sample.pdf`，不依赖手动建立内存索引
- [ ] 已使用 `CASE_LIMIT=1` 成功验证单题调用和结果保存
- [ ] 已改为 `CASE_LIMIT=None`，按顺序运行全部 12 道题
- [ ] 已生成独立的 `data/evaluation/baseline_results.json`
- [ ] 每道成功案例都保存了 `retrieved_sources` 和 `model_answer`
- [ ] 已对 10 道可回答问题人工填写 `retrieval_hit`
- [ ] 已对全部 12 道问题人工填写 `answer_correct`
- [ ] 两道无答案题的 `retrieval_hit` 保持为 `null`
- [ ] 已计算并记录检索命中率、回答正确率和各类型正确情况
- [ ] 已确认今天没有调整 Chunk、overlap、top-k 或 RAG 业务逻辑
- [ ] 测试成功后完成 Git 提交，并确认工作区干净

实际完成：已完成

遇到的卡点：暂无

Git commit：已提交
