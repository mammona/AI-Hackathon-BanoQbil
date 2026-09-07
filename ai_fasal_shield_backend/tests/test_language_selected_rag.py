import numpy as np

from app.constants.symptoms import (
    SYMPTOM_CONCEPTS,
    SYMPTOM_DICTIONARY_VERSION,
    SymptomCode,
)
from app.models.schemas import FarmerInput, ReportLanguage
from app.services.symptom_rag_service import SymptomRAGService


class RecordingEmbedder:
    def __init__(self) -> None:
        self.document_calls: list[tuple[str, list[str]]] = []
        self.query_calls: list[tuple[str, list[str]]] = []

    def encode_documents(self, texts: list[str], *, language: str) -> np.ndarray:
        self.document_calls.append((language, list(texts)))
        # Stable normalized dummy vectors, one row per document.
        out = np.zeros((len(texts), 3), dtype=np.float32)
        if len(texts):
            out[:, 0] = 1.0
        return out

    def encode_queries(self, texts: list[str], *, language: str) -> np.ndarray:
        self.query_calls.append((language, list(texts)))
        out = np.zeros((len(texts), 3), dtype=np.float32)
        if len(texts):
            out[:, 0] = 1.0
        return out


def test_language_enum_supports_mobile_aliases():
    assert ReportLanguage("urdu") == ReportLanguage.urdu
    assert ReportLanguage("ur") == ReportLanguage.urdu
    assert ReportLanguage("pa") == ReportLanguage.punjabi
    assert ReportLanguage("shahmukhi") == ReportLanguage.punjabi
    assert ReportLanguage("en") == ReportLanguage.english
    assert ReportLanguage("Punjabi") == ReportLanguage.punjabi
    assert ReportLanguage("English") == ReportLanguage.english


def test_farmer_input_keeps_report_language():
    farmer = FarmerInput(
        language="punjabi",
        symptoms_raw="پتے پیلے ہو رہے نیں",
        onset_raw="",
        affected_extent_raw="",
        spread_raw="",
    )
    assert farmer.language == ReportLanguage.punjabi


def test_all_concepts_have_urdu_and_punjabi_meanings():
    for concept in SYMPTOM_CONCEPTS.values():
        urdu = concept.semantic_text_for("urdu")
        punjabi = concept.semantic_text_for("punjabi")
        english = concept.semantic_text_for("english")
        assert urdu.strip()
        assert punjabi.strip()
        assert english.strip()
        assert urdu != english
        assert punjabi != english


def test_selected_language_builds_only_that_language_concept_matrix():
    embedder = RecordingEmbedder()
    service = SymptomRAGService(embedder=embedder)

    service._concept_matrix("cotton", "urdu")
    assert len(embedder.document_calls) == 1
    language, documents = embedder.document_calls[-1]
    assert language == "urdu"
    assert any("پتے" in text for text in documents)
    assert not any("Leaves become specifically yellow" in text for text in documents)

    service._concept_matrix("cotton", "punjabi")
    assert len(embedder.document_calls) == 2
    language, documents = embedder.document_calls[-1]
    assert language == "punjabi"
    assert any("نیں" in text or "اے" in text for text in documents)

    service._concept_matrix("cotton", "english")
    assert len(embedder.document_calls) == 3
    language, documents = embedder.document_calls[-1]
    assert language == "english"
    assert any("yellow" in text.lower() for text in documents)


def test_cache_is_separate_for_each_language():
    embedder = RecordingEmbedder()
    service = SymptomRAGService(embedder=embedder)

    service._concept_matrix("cotton", "urdu")
    service._concept_matrix("cotton", "urdu")
    service._concept_matrix("cotton", "punjabi")

    assert [call[0] for call in embedder.document_calls] == ["urdu", "punjabi"]


def test_query_embedding_uses_same_selected_language():
    embedder = RecordingEmbedder()
    service = SymptomRAGService(embedder=embedder)

    service.retrieve(
        "پتے پیلے ہو رہے ہیں",
        crop="cotton",
        affected_part="leaves",
        language="urdu",
    )
    assert embedder.query_calls[-1][0] == "urdu"

    service.retrieve(
        "پتے پیلے ہو رہے نیں",
        crop="cotton",
        affected_part="leaves",
        language="punjabi",
    )
    assert embedder.query_calls[-1][0] == "punjabi"


def test_dictionary_version_bumped_for_clean_language_selected_rag():
    assert SYMPTOM_DICTIONARY_VERSION == "7.0"


def test_yellowing_concept_is_specific_in_all_three_languages():
    concept = SYMPTOM_CONCEPTS[SymptomCode.LEAF_YELLOWING]
    assert "yellow" in concept.semantic_text_for("english").lower()
    assert "پیلے" in concept.semantic_text_for("urdu")
    assert "پیلے" in concept.semantic_text_for("punjabi")


def test_punjabi_yellowing_retrieval_text_is_short_positive_only():
    text = SYMPTOM_CONCEPTS[SymptomCode.LEAF_YELLOWING].semantic_text_for("punjabi")
    assert "پیلے" in text or "زرد" in text
    assert "مرجھ" not in text
    assert "سوراخ" not in text


def test_urdu_yellowing_retrieval_text_is_short_positive_only():
    text = SYMPTOM_CONCEPTS[SymptomCode.LEAF_YELLOWING].semantic_text_for("urdu")
    assert "پیلے" in text or "زرد" in text
    assert "مرجھ" not in text
    assert "سوراخ" not in text


def test_curling_retrieval_text_does_not_contain_spot_terms():
    urdu = SYMPTOM_CONCEPTS[SymptomCode.LEAF_CURLING].semantic_text_for("urdu")
    punjabi = SYMPTOM_CONCEPTS[SymptomCode.LEAF_CURLING].semantic_text_for("punjabi")
    assert "دھب" not in urdu
    assert "دھب" not in punjabi
