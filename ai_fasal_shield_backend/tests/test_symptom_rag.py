import numpy as np

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import RetrievedCandidate, SymptomRAGService


class DummyEmbedder:
    def encode_queries(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return np.ones((len(texts), 3), dtype=np.float32)

    def encode_documents(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return np.ones((len(texts), 3), dtype=np.float32)


def candidate(code: SymptomCode, score: float) -> RetrievedCandidate:
    return RetrievedCandidate(
        code=code,
        name=code.value.replace("_", " ").title(),
        description="test",
        plant_part="leaves",
        score=score,
        retrieval_language="urdu",
    )


def test_below_threshold_goes_to_others(monkeypatch):
    service = SymptomRAGService(embedder=DummyEmbedder())
    service.settings.symptom_match_threshold = 0.55
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *args, **kwargs: [
            candidate(SymptomCode.LEAF_YELLOWING, 0.42),
            candidate(SymptomCode.LEAF_DISCOLORATION, 0.38),
        ],
    )

    code, mapping, _ = service.map_one(
        "کوئی عجیب چپچپا مادہ",
        crop="cotton",
        affected_part="leaves",
        language="urdu",
    )

    assert code == SymptomCode.OTHERS_MAP
    assert mapping.status == "below_threshold"


def test_good_score_and_margin_maps_semantically(monkeypatch):
    service = SymptomRAGService(embedder=DummyEmbedder())
    service.settings.symptom_match_threshold = 0.55
    service.settings.symptom_min_margin = 0.05
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *args, **kwargs: [
            candidate(SymptomCode.LEAF_CURLING, 0.84),
            candidate(SymptomCode.LEAF_WILTING, 0.63),
        ],
    )

    code, mapping, _ = service.map_one(
        "پتے مڑ رہے ہیں",
        crop="rice",
        affected_part="leaves",
        language="urdu",
    )

    assert code == SymptomCode.LEAF_CURLING
    assert mapping.status == "matched_semantic"
    assert mapping.margin is not None and mapping.margin > 0.05


def test_near_tie_becomes_others_instead_of_llm_rerank(monkeypatch):
    service = SymptomRAGService(embedder=DummyEmbedder())
    service.settings.symptom_match_threshold = 0.55
    service.settings.symptom_min_margin = 0.05
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *args, **kwargs: [
            candidate(SymptomCode.LEAF_BROWN_SPOTS, 0.72),
            candidate(SymptomCode.LEAF_LESIONS, 0.70),
        ],
    )

    code, mapping, _ = service.map_one(
        "پتوں پر نشان ہیں",
        crop="rice",
        affected_part="leaves",
        language="urdu",
        use_reranker=False,
    )

    assert code == SymptomCode.OTHERS_MAP
    assert mapping.status == "ambiguous"


def test_enrich_uses_canonical_english_display_but_keeps_raw_mapping(monkeypatch):
    from app.models.schemas import Assessment

    service = SymptomRAGService(embedder=DummyEmbedder())

    def fake_map(span, **kwargs):
        code = (
            SymptomCode.LEAF_YELLOWING
            if "پیلے" in span
            else SymptomCode.LEAF_CURLING
        )
        from app.models.schemas import SymptomMappingItem
        item = SymptomMappingItem(
            symptom=span,
            code=code,
            concept_name=("Leaf yellowing" if code == SymptomCode.LEAF_YELLOWING else "Leaf curling"),
            similarity=0.9,
            second_best_similarity=0.7,
            margin=0.2,
            status="matched_semantic",
        )
        return code, item, []

    monkeypatch.setattr(service, "map_one", fake_map)
    assessment = Assessment(
        symptoms=["پتے پیلے ہو رہے ہیں", "مڑ رہے ہیں"],
        affected_part="leaves",
    )

    result = service.enrich_assessment(assessment, crop="cotton", language="urdu")

    assert result.symptoms == ["leaf yellowing", "leaf curling"]
    assert result.symptom_codes == [
        SymptomCode.LEAF_YELLOWING,
        SymptomCode.LEAF_CURLING,
    ]
    assert result.symptom_mapping[0].symptom == "پتے پیلے ہو رہے ہیں"


def test_v10_query_contains_only_original_symptom_meaning():
    query = SymptomRAGService.build_query_text(
        "پتے پیلے ہو رہے ہیں",
        crop="cotton",
        affected_part="leaves",
    )
    assert query == "پتے پیلے ہو رہے ہیں"
    assert "cotton" not in query.lower()
    assert "affected plant part" not in query.lower()


def test_eligible_concepts_are_filtered_by_crop_and_part():
    service = SymptomRAGService(embedder=DummyEmbedder())
    concepts = service.eligible_concepts(crop="cotton", affected_part="leaves")
    assert concepts
    assert all(c.plant_part == "leaves" for c in concepts)
    assert all("cotton" in c.crops for c in concepts)
    assert all(c.code != SymptomCode.PANICLE_DRYING for c in concepts)


def test_v10_concept_vectors_are_meaning_only_without_crop_metadata():
    from app.constants.symptoms import SYMPTOM_CONCEPTS

    yellow = SYMPTOM_CONCEPTS[SymptomCode.LEAF_YELLOWING].semantic_text.lower()
    generic = SYMPTOM_CONCEPTS[SymptomCode.LEAF_DISCOLORATION].semantic_text.lower()
    assert "yellow" in yellow
    assert "abnormal colour" in generic
    assert "applicable crop" not in yellow
    assert "affected plant part" not in yellow
    assert "cotton" not in yellow


def test_parent_child_near_tie_does_not_bypass_reranker(monkeypatch):
    service = SymptomRAGService(embedder=DummyEmbedder())
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *args, **kwargs: [
            candidate(SymptomCode.LEAF_YELLOWING, 0.70),
            candidate(SymptomCode.LEAF_DISCOLORATION, 0.69),
        ],
    )

    # With reranking disabled, the near tie must now remain ambiguous. The old
    # matched_specific_over_parent shortcut is intentionally gone.
    code, mapping, _ = service.map_one(
        "پتے پیلے ہو رہے ہیں",
        crop="cotton",
        affected_part="leaves",
        language="urdu",
        use_reranker=False,
    )

    assert code == SymptomCode.OTHERS_MAP
    assert mapping.status == "ambiguous"


def test_generic_parent_does_not_beat_specific_child_on_near_tie(monkeypatch):
    service = SymptomRAGService(embedder=DummyEmbedder())
    service.settings.symptom_match_threshold = 0.55
    service.settings.symptom_min_margin = 0.05
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *args, **kwargs: [
            candidate(SymptomCode.LEAF_DISCOLORATION, 0.70),
            candidate(SymptomCode.LEAF_YELLOWING, 0.69),
        ],
    )

    code, mapping, _ = service.map_one(
        "پتے پیلے ہو رہے ہیں",
        crop="cotton",
        affected_part="leaves",
        language="urdu",
        use_reranker=False,
    )

    assert code == SymptomCode.OTHERS_MAP
    assert mapping.status == "ambiguous"
