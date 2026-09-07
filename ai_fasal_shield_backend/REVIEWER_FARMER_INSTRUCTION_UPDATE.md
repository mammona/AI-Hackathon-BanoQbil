# Reviewer farmer instruction update

The alert confirmation panel now separates two reviewer fields:

- **Verification note**: private/admin-only and never sent to farmers.
- **Farmer instruction**: Punjabi/Shahmukhi guidance that is intentionally appended to the farmer notification.

On AMBER -> RED, the backend builds a dynamic Punjabi alert using crop, disease/problem, common symptoms and distance, then appends:

`زرعی ماہر دی ہدایت: <farmer_instruction>`

If an already-confirmed RED alert is confirmed again with changed farmer guidance, the existing device notification is updated rather than duplicated and is marked unread again.

Existing SQLite databases are migrated additively with `alerts.farmer_instruction`; no reset is needed.
