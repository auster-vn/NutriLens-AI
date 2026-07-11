from app.rag.service import KnowledgeDocument, answer_question, search_knowledge


def test_rag_search_returns_citation_for_sugar():
    results = search_knowledge("Đường cao trong sản phẩm nghĩa là gì?")

    assert results
    assert any(result.source == "sugar_guidance.md" for result in results)


def test_rag_answer_excludes_weakly_related_documents():
    response = answer_question("Đường cao trên nhãn dinh dưỡng nghĩa là gì?")

    assert {citation.source for citation in response.citations} == {"sugar_guidance.md"}


def test_rag_ranks_protein_guidance_above_generic_label_matches():
    response = answer_question("Protein trên nhãn dinh dưỡng có ý nghĩa gì?")

    assert response.citations[0].source == "protein_basics.md"
    assert "sugar_guidance.md" not in {citation.source for citation in response.citations}


def test_rag_abstains_without_evidence():
    response = answer_question("XZ-991 chữa bệnh gì?")

    assert response.abstained is True
    assert response.citations == []


def test_approved_admin_document_can_ground_an_answer():
    document = KnowledgeDocument(
        filename="custom_fiber.md",
        title="Custom fiber guidance",
        metadata={"domains": ["fiber", "nutrition"], "source_url": "https://example.com/fiber"},
        body="Chất xơ hòa tan hỗ trợ cảm giác no và là một phần của chế độ ăn cân bằng.",
    )

    response = answer_question("Chất xơ hòa tan có lợi ích dinh dưỡng gì?", additional_documents=[document])

    assert response.abstained is False
    assert any(citation.source == document.filename for citation in response.citations)
