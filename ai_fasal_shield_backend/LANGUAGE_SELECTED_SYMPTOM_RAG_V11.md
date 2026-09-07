# V11: Language-Selected Multilingual Symptom RAG

## Decision

The report carries an explicit language parameter from the mobile app. This avoids runtime translation and avoids comparing a short Urdu/Punjabi symptom only against English concept descriptions.

Supported values:

```text
english
urdu
punjabi   # Pakistani Punjabi, Shahmukhi script
```

## Runtime pipeline

```text
raw Q1
  ↓
Qwen extracts verbatim symptom spans and an affected-part proposal
  ↓
Python validates explicit plant-part evidence
  ↓
crop + plant-part hard filtering
  ↓
select concept language from request
  ↓
embed query + only that language's candidate definitions
  ↓
Top-3 similarity
  ↓
threshold + margin
  ↓
canonical code / OTHERS_MAP
```

### Example

Request:

```text
language=urdu
answer_1=پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں
```

Q1 spans:

```text
پتے پیلے ہو رہے ہیں
پتے مڑ رہے ہیں
```

RAG compares these only with Urdu concept definitions. English and Punjabi vectors do not participate in this report's ranking.

## Why this is efficient

There are only 40 canonical symptom concepts. Concept embeddings are cached by:

```text
(crop, language)
```

So once the Urdu cotton concept matrix has been embedded, later Urdu cotton reports only embed the incoming symptom spans and run a tiny NumPy cosine-similarity operation.

No vector database is required.

## Safety

- below similarity threshold → `OTHERS_MAP`
- insufficient Top1/Top2 margin → `OTHERS_MAP`
- clear match → canonical code
- specific child concept may beat its own generic parent on a close score
- Qwen's affected-part proposal is checked against explicit raw plant-part evidence
- symptom text itself is never changed by the Python plant-part validator

## Files

```text
app/constants/symptoms.py
    40 concepts + English/Urdu/Punjabi semantic definitions

app/models/schemas.py
    ReportLanguage + report language fields

app/api/reports.py
    required multipart `language` form parameter

app/services/symptom_rag_service.py
    selected-language cache/retrieval logic

app/services/report_service.py
    passes report language into RAG and persists it

app/models/database_models.py
    stores report language

scripts/evaluate_language_selected_rag.py
    10 equivalent cases in each supported language
```
