from src.rag_pipeline import build_context


def test_build_context_joins_documents_in_order():
    docs = [
        {"document": "First film", "metadata": {"title": "A"}},
        {"document": "Second film", "metadata": {"title": "B"}},
    ]

    context = build_context(docs)

    assert context == "First film\n\n---\n\nSecond film"
