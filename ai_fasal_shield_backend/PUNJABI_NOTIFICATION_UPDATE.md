# Punjabi Farmer Notification Update

This update changes only the farmer-facing confirmed-alert message layer.

## Confirmed flow

`AMBER -> expert confirms -> RED -> eligible devices -> Punjabi notification`

## Important separation

- `alerts.verification_note` remains an internal expert/admin note.
- The farmer notification is generated from the confirmed alert's crop, disease, canonical symptoms, alert center/radius and each device's distance.
- The verification note is never copied into `notifications.message`.

## Farmer-facing language

For the current prototype:

- `notifications.title` = Punjabi Shahmukhi
- `notifications.message` = Punjabi Shahmukhi
- `notifications.message_local` = same Punjabi Shahmukhi text
- `notifications.language` = `punjabi`

Canonical database values remain English codes for outbreak matching.

## Example

```text
تصدیق شدہ فصل بیماری الرٹ

تہاڈے علاقے دے نیڑے کپاس دی فصل وچ پتیاں دے مڑن والی وائرس بیماری دی تصدیق ہوئی اے۔
عام علامتاں: پتے مڑنا، پتے پیلے ہونا۔
اپنی فصل دا معائنہ کرو، تے جے ایہ علامتاں نظر آون تے AI Fasal Shield تے رپورٹ جمع کرو۔
علاج یا سپرے دی رہنمائی لئی زرعی ماہر نال رابطہ کرو۔
```

No database reset is required for the code change. Existing notification rows keep their old text; newly confirmed RED alerts create Punjabi notifications.
