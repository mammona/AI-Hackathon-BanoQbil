# AI Fasal Shield V17 - Farmer Device & Confirmed Alert Notification Flow

## Purpose
This backend completes the prototype loop from outbreak detection to expert confirmation and farmer notification readiness.

## Flow
1. Mobile app installs and creates a stable `device_id`.
2. App registers the device with crop(s), preferred language and current GPS.
3. Farmer reports are processed normally. `device_id` is optional and can be attached to a report.
4. Outbreak engine creates `MONITORING` / `AMBER` signals.
5. Admin dashboard opens an AMBER alert and shows how many registered same-crop devices are inside the alert radius.
6. Expert clicks **Confirm -> RED & Notify Farmers**.
7. Backend promotes AMBER to RED, stores expert verification, finds eligible farmer devices, and creates one persistent in-app notification per eligible device.
8. Backend stores the farmer-facing alert text in Punjabi (Shahmukhi). The expert verification note remains internal and is never used as the farmer message.
9. Mobile app later calls the device notification API and displays unread alerts.
10. Mobile marks a notification read after the farmer opens it.

## New database tables
### `registered_devices`
Stores:
- `device_id`
- optional `push_token` for later FCM integration
- crops
- preferred language
- latitude / longitude
- location availability
- notifications enabled
- last seen / timestamps

### `notifications`
Stores:
- notification id
- alert id
- device id
- crop
- Punjabi (Shahmukhi) farmer title/message
- duplicate `message_local` Punjabi value for mobile compatibility
- distance from outbreak center
- unread/read status
- created/read timestamps

A unique `(alert_id, device_id)` constraint prevents duplicate farmer notifications when an expert confirms the same RED alert again.

## Device targeting rule
A device receives an in-app notification only when:
- notifications are enabled
- latest location is available
- the device follows the same crop as the alert
- Haversine distance from the alert center is `<= alert.radius_km` (default 5 km)

## APIs
### Register / refresh an app installation
`POST /api/v1/devices/register`

Example:
```json
{
  "device_id": "PHONE-DEMO-001",
  "crops": ["cotton"],
  "preferred_language": "punjabi",
  "latitude": 31.5208,
  "longitude": 74.3590,
  "push_token": null,
  "notifications_enabled": true
}
```

### Update latest phone location
`PUT /api/v1/devices/{device_id}/location`

### List registered devices (admin/testing)
`GET /api/v1/devices`

### Farmer app fetches its alerts
`GET /api/v1/devices/{device_id}/notifications`

Use `?unread_only=true` for unread alerts only.

### Farmer opens a notification
`POST /api/v1/notifications/{notification_id}/read`

### Expert confirms outbreak
`POST /api/v1/alerts/{alert_id}/verify`

```json
{
  "decision": "confirmed",
  "expert_name": "Agriculture Officer",
  "note": "Field verification confirms outbreak."
}
```

Confirmation performs both actions in one backend transaction flow:
- AMBER -> RED
- create notifications for eligible farmer devices

The response includes:
- `eligible_device_count`
- `notification_count`

## Admin dashboard
Open:
`http://127.0.0.1:8000/admin`

For an AMBER alert the review panel now shows:
- eligible farmer devices inside the radius
- notifications already created
- **Confirm -> RED & Notify Farmers** button
- Reject alert button

The top summary also shows registered devices and unread farmer notifications.

## Demo before Flutter is connected
Seed deterministic outbreak reports:
```powershell
python -m scripts.seed_e2e_demo_reports --reset-all
```

Seed six farmer devices:
```powershell
python -m scripts.seed_demo_devices
```

Start FastAPI and open `/admin`. Confirm the 3-report Cotton AMBER alert. Three nearby Cotton devices should receive notifications; the nearby Rice device, far Cotton device and no-GPS device must not receive one.

Inspect rows:
```powershell
python -m scripts.check_demo_notifications
```

## Important prototype scope
This version implements **persistent in-app notification delivery in the backend**. It does not yet call Firebase Cloud Messaging. The optional `push_token` is already stored so FCM can be connected when the Flutter mobile phase starts.


## Punjabi farmer-message policy
For the current prototype, every farmer-facing confirmed alert is generated deterministically in Punjabi (Shahmukhi), regardless of the device's saved preferred-language setting.

The backend keeps canonical values such as `cotton`, `curl_virus`, and `LEAF_CURLING` for SQL, matching and analytics, but converts them to farmer-friendly Punjabi in the notification text.

Example:

```text
تصدیق شدہ فصل بیماری الرٹ

تہاڈے علاقے دے نیڑے کپاس دی فصل وچ پتیاں دے مڑن والی وائرس بیماری دی تصدیق ہوئی اے۔
عام علامتاں: پتے مڑنا، پتے پیلے ہونا۔
اپنی فصل دا معائنہ کرو، تے جے ایہ علامتاں نظر آون تے AI Fasal Shield تے رپورٹ جمع کرو۔
```

### Expert verification note is separate
`alerts.verification_note` is an internal expert/admin field. It is saved with the alert for audit/review, but the notification generator does not receive or copy that note into the farmer message.

This prevents internal notes such as lab observations, uncertainty, or operational comments from being sent directly to farmers.
