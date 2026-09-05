/// Converts raw offline-ASR output into Shahmukhi (Urdu script).
///
/// The Omnilingual ASR model transcribes Punjabi speech in Gurmukhi, and
/// in Devanagari when it mislabels the language as Hindi. Every
/// farmer-facing string in this app is Shahmukhi, so transcripts are
/// transliterated character-wise here. Characters outside the
/// Devanagari/Gurmukhi blocks (including already-Shahmukhi text) pass
/// through untouched, which keeps the conversion idempotent.
///
/// Short vowels are dropped and long vowels written out, following Urdu
/// orthography (e.g. कितना / ਕਿਤਨਾ -> کتنا).
class ScriptNormalizer {
  ScriptNormalizer._();

  static String toShahmukhi(String text) {
    final sb = StringBuffer();
    final runes = text.runes.toList();
    for (var i = 0; i < runes.length; i++) {
      final r = runes[i];
      final next = i + 1 < runes.length ? runes[i + 1] : null;
      if (next == 0x093C || next == 0x0A3C) {
        final combined = _nuktaForms[r];
        if (combined != null) {
          sb.write(combined);
          i++;
          continue;
        }
      }
      final mapped = _devanagari[r] ?? _gurmukhi[r];
      if (mapped != null) {
        sb.write(mapped);
        continue;
      }
      if ((r >= 0x0966 && r <= 0x096F) || (r >= 0x0A66 && r <= 0x0A6F)) {
        sb.writeCharCode(0x30 + (r >= 0x0966 ? r - 0x0966 : r - 0x0A66));
        continue;
      }
      sb.writeCharCode(r);
    }
    return sb.toString();
  }

  static const Map<int, String> _devanagari = {
    // Nasalization marks and visarga.
    0x0900: 'ں', 0x0901: 'ں', 0x0902: 'ں', 0x0903: '',
    // Independent vowels.
    0x0904: 'ا', 0x0905: 'ا', 0x0906: 'آ', 0x0907: 'ا', 0x0908: 'ای',
    0x0909: 'ا', 0x090A: 'او', 0x090B: 'ر', 0x090C: 'ر', 0x090D: 'ا',
    0x090E: 'ا', 0x090F: 'ای', 0x0910: 'ای', 0x0911: 'او', 0x0912: 'او',
    0x0913: 'او', 0x0914: 'او',
    // Consonants.
    0x0915: 'ک', 0x0916: 'کھ', 0x0917: 'گ', 0x0918: 'گھ', 0x0919: 'نگ',
    0x091A: 'چ', 0x091B: 'چھ', 0x091C: 'ج', 0x091D: 'جھ', 0x091E: 'نج',
    0x091F: 'ٹ', 0x0920: 'ٹھ', 0x0921: 'ڈ', 0x0922: 'ڈھ', 0x0923: 'ݨ',
    0x0924: 'ت', 0x0925: 'تھ', 0x0926: 'د', 0x0927: 'دھ', 0x0928: 'ن',
    0x0929: 'ن', 0x092A: 'پ', 0x092B: 'پھ', 0x092C: 'ب', 0x092D: 'بھ',
    0x092E: 'م', 0x092F: 'ی', 0x0930: 'ر', 0x0931: 'ر', 0x0932: 'ل',
    0x0933: 'ل', 0x0934: 'ل', 0x0935: 'و', 0x0936: 'ش', 0x0937: 'ش',
    0x0938: 'س', 0x0939: 'ہ',
    0x093D: '',
    // Dependent vowel signs (matras).
    0x093E: 'ا', 0x093F: '', 0x0940: 'ی', 0x0941: '', 0x0942: 'و',
    0x0943: '', 0x0944: 'و', 0x0945: '', 0x0946: 'ے', 0x0947: 'ے',
    0x0948: 'ے', 0x0949: 'ا', 0x094A: 'و', 0x094B: 'و', 0x094C: 'و',
    // Halant: conjuncts collapse into consonant clusters.
    0x094D: '',
    // Danda punctuation.
    0x0964: '۔', 0x0965: '۔',
  };

  static const Map<int, String> _gurmukhi = {
    0x0A01: 'ں', 0x0A02: 'ں', 0x0A03: '',
    0x0A05: 'ا', 0x0A06: 'آ', 0x0A07: 'ای', 0x0A08: 'ای', 0x0A09: 'و',
    0x0A0A: 'او', 0x0A0F: 'ای', 0x0A10: 'ای', 0x0A13: 'او', 0x0A14: 'او',
    0x0A15: 'ک', 0x0A16: 'کھ', 0x0A17: 'گ', 0x0A18: 'گھ', 0x0A19: 'نگ',
    0x0A1A: 'چ', 0x0A1B: 'چھ', 0x0A1C: 'ج', 0x0A1D: 'جھ', 0x0A1E: 'نج',
    0x0A1F: 'ٹ', 0x0A20: 'ٹھ', 0x0A21: 'ڈ', 0x0A22: 'ڈھ', 0x0A23: 'ݨ',
    0x0A24: 'ت', 0x0A25: 'تھ', 0x0A26: 'د', 0x0A27: 'دھ', 0x0A28: 'ن',
    0x0A2A: 'پ', 0x0A2B: 'پھ', 0x0A2C: 'ب', 0x0A2D: 'بھ', 0x0A2E: 'م',
    0x0A2F: 'ی', 0x0A30: 'ر', 0x0A32: 'ل', 0x0A33: 'ل', 0x0A35: 'و',
    0x0A36: 'ش', 0x0A38: 'س', 0x0A39: 'ہ',
    0x0A3E: 'ا', 0x0A3F: '', 0x0A40: 'ی', 0x0A41: '', 0x0A42: 'و',
    0x0A47: 'ے', 0x0A48: 'ے', 0x0A4B: 'و', 0x0A4C: 'و',
    0x0A4D: '',
    0x0A70: 'ں', // tippi
    0x0A71: '', // addak (gemination)
  };

  /// Base consonant + nukta (0x093C / 0x0A3C) pairs, e.g. ख़ -> خ.
  static const Map<int, String> _nuktaForms = {
    0x0915: 'ق', 0x0916: 'خ', 0x0917: 'غ', 0x091C: 'ز', 0x0921: 'ڑ',
    0x0922: 'ڑھ', 0x092B: 'ف', 0x092F: 'ی',
    0x0A16: 'خ', 0x0A17: 'غ', 0x0A1C: 'ز', 0x0A2B: 'ف', 0x0A32: 'ل',
    0x0A36: 'ش', 0x0A38: 'ش',
  };
}
