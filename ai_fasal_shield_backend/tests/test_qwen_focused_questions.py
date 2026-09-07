from app.models.schemas import FarmerInput
from app.services.qwen_report_service import (
    Q1Result,
    Q2Result,
    Q3Result,
    Q4Result,
    QwenReportService,
)


def test_missing_answers_are_skipped(monkeypatch):
    service = QwenReportService()
    calls: list[str] = []

    def fake_call(**kwargs):
        calls.append(kwargs["stage"])
        model = kwargs["response_model"]
        if model is Q1Result:
            return Q1Result(
                symptom_spans=["پتے پیلے ہیں"],
                affected_part="leaves",
            )
        if model is Q3Result:
            return Q3Result(affected_area="20 plants")
        raise AssertionError("Missing Q2/Q4 should not call Qwen")

    monkeypatch.setattr(service, "_call_qwen", fake_call)

    result = service.generate(
        FarmerInput(
            symptoms_raw="پتے پیلے ہیں",
            onset_raw="",
            affected_extent_raw="بیس پودے متاثر ہیں",
            spread_raw="   ",
        )
    )

    assert calls == ["Q1 verbatim symptom spans", "Q3 affected extent"]
    assert result.symptoms == ["پتے پیلے ہیں"]
    assert result.problem_duration is None
    assert result.affected_area == "20 plants"
    assert result.spread_status is None


def test_all_four_answers_use_four_focused_calls_and_keep_q1_raw(monkeypatch):
    service = QwenReportService()
    calls: list[str] = []

    def fake_call(**kwargs):
        calls.append(kwargs["stage"])
        model = kwargs["response_model"]
        if model is Q1Result:
            return Q1Result(
                symptom_spans=["پتے پیلے ہو رہے ہیں", "مڑ رہے ہیں"],
                affected_part="leaves",
            )
        if model is Q2Result:
            return Q2Result(problem_duration="3 days")
        if model is Q3Result:
            return Q3Result(affected_area="0.5 acre")
        if model is Q4Result:
            return Q4Result(spread_status="spreading")
        raise AssertionError(model)

    monkeypatch.setattr(service, "_call_qwen", fake_call)

    result = service.generate(
        FarmerInput(
            symptoms_raw="پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں",
            onset_raw="تین دن پہلے شروع ہوا",
            affected_extent_raw="تقریباً آدھا ایکڑ متاثر ہے",
            spread_raw="ہاں مسئلہ پھیل رہا ہے",
        )
    )

    assert calls == [
        "Q1 verbatim symptom spans",
        "Q2 duration",
        "Q3 affected extent",
        "Q4 spread",
    ]
    assert result.symptoms == ["پتے پیلے ہو رہے ہیں", "پتے مڑ رہے ہیں"]
    assert result.affected_part == "leaves"
    assert result.problem_duration == "3 days"
    assert result.affected_area == "0.5 acre"
    assert result.spread_status == "spreading"


def test_q1_translation_or_paraphrase_is_rejected_and_raw_is_split(monkeypatch):
    service = QwenReportService()

    def fake_call(**kwargs):
        if kwargs["response_model"] is Q1Result:
            # This reproduces the V7 failure: Qwen changed the meaning.
            return Q1Result(
                symptom_spans=["leaf browning", "leaf curling"],
                affected_part="whole plant",
            )
        raise AssertionError("Only Q1 should be called")

    monkeypatch.setattr(service, "_call_qwen", fake_call)

    result = service.generate(
        FarmerInput(
            symptoms_raw="پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں",
            onset_raw="",
            affected_extent_raw="",
            spread_raw="",
        )
    )

    # The translated hallucination is discarded. Evidence comes from raw Q1.
    assert result.symptoms == ["پتے پیلے ہو رہے ہیں", "پتے مڑ رہے ہیں"]
    assert "leaf browning" not in result.symptoms


def test_shared_stem_subject_is_propagated_after_split():
    service = QwenReportService()
    spans = service._validated_original_spans(
        "تنا کالا ہو رہا ہے اور کمزور بھی ہے",
        ["تنا کالا ہو رہا ہے", "کمزور بھی ہے"],
    )
    assert spans == ["تنا کالا ہو رہا ہے", "تنا کمزور بھی ہے"]


def test_context_is_not_propagated_when_two_parts_are_explicit():
    service = QwenReportService()
    spans = service._validated_original_spans(
        "پتے پیلے ہیں اور تنا کمزور ہے",
        ["پتے پیلے ہیں", "تنا کمزور ہے"],
    )
    assert spans == ["پتے پیلے ہیں", "تنا کمزور ہے"]


def test_punjabi_te_conjunction_is_split_into_distinct_observations():
    service = QwenReportService()
    spans = service._validated_original_spans(
        "پتیاں دے سرے سک رہے نیں تے پیلاپن تھلے ول پھیل رہیا اے",
        ["پتیاں دے سرے سک رہے نیں تے پیلاپن تھلے ول پھیل رہیا اے"],
    )
    assert spans == [
        "پتیاں دے سرے سک رہے نیں",
        "پتیاں پیلاپن تھلے ول پھیل رہیا اے",
    ]
