from app.constants.plant_parts import validate_affected_part


def test_raw_leaf_word_overrides_wrong_whole_plant():
    raw = "پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں"
    assert validate_affected_part(raw, "whole plant") == "leaves"


def test_raw_whole_plant_word_is_preserved():
    raw = "پودا مرجھا رہا ہے"
    assert validate_affected_part(raw, "leaves") == "whole plant"


def test_qwen_value_is_kept_when_raw_part_is_not_explicit():
    assert validate_affected_part("رنگ بدل رہا ہے", "leaves") == "leaves"


def test_raw_leaf_word_fills_missing_qwen_part():
    raw = "پتے پیلے ہو رہے ہیں"
    assert validate_affected_part(raw, None) == "leaves"


def test_punjabi_shahmukhi_leaf_word_is_detected():
    assert validate_affected_part("پتیاں پیلیاں ہو رہیاں نیں", None) == "leaves"


def test_punjabi_shahmukhi_root_word_is_detected():
    assert validate_affected_part("جڑاں کالی ہو رہیاں نیں", None) == "roots"


def test_punjabi_boota_is_whole_plant():
    assert validate_affected_part("بوٹا مرجھا رہیا اے", None) == "whole plant"
