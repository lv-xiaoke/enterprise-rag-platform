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
CASE_LIMIT: int | None = None


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