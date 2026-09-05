import 'package:fasal_guard_mobile/services/script_normalizer.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Devanagari transcript becomes Shahmukhi', () {
    expect(
      ScriptNormalizer.toShahmukhi('तीन करोड़ तीन करोड़ तीन करोड़ अकबा'),
      'تین کروڑ تین کروڑ تین کروڑ اکبا',
    );
  });

  test('Gurmukhi transcript becomes Shahmukhi', () {
    expect(
      ScriptNormalizer.toShahmukhi('ਨੀ ਆਰ ਸਰ ਡੇ ਗਾਉਂਚ ਦੇ ਵਿੱਚ ਹੈ'),
      'نی آر سر ڈے گاوںچ دے وچ ہے',
    );
  });

  test('Shahmukhi, digits and latin pass through unchanged', () {
    const text = 'کیہ مسئلہ ودھ رہیا اے 3 acre ok';
    expect(ScriptNormalizer.toShahmukhi(text), text);
  });

  test('conversion is idempotent', () {
    const gurmukhi = 'ਪੰਜ ਏਕੜ';
    final once = ScriptNormalizer.toShahmukhi(gurmukhi);
    expect(ScriptNormalizer.toShahmukhi(once), once);
  });

  test('nukta forms map to single Urdu letters', () {
    expect(ScriptNormalizer.toShahmukhi('ख़'), 'خ');
    expect(ScriptNormalizer.toShahmukhi('ਸ਼'), 'ش');
  });

  test('native digits become ASCII digits', () {
    expect(ScriptNormalizer.toShahmukhi('३'), '3');
  });
}
