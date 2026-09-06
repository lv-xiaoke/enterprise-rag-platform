import pytest
from pydantic import ValidationError

from app.models import KnowledgeBaseQueryRequest


def test_query_request_normalizes_valid_question() -> None:
    request = KnowledgeBaseQueryRequest(
        question="  员工如何请假？  ",
        top_k=3,
    )

    assert request.question == "员工如何请假？"
    assert request.top_k == 3


@pytest.mark.parametrize(
    ("question", "top_k"),
    [
        ("   ", 3),
        ("合法问题", 0),
        ("合法问题", 11),
    ],
)
def test_query_request_rejects_invalid_input(
    question: str,
    top_k: int,
) -> None:
    with pytest.raises(ValidationError):
        KnowledgeBaseQueryRequest(
            question=question,
            top_k=top_k,
        )