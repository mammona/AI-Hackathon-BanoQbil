from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.database_models import Alert, Notification, RegisteredDevice
from app.repositories.device_repository import DeviceRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.outbreak_service import OutbreakService


class NotificationService:
    """Create farmer-facing notifications for expert-confirmed RED alerts.

    Prototype policy:
    - farmer-facing notification text is Punjabi (Shahmukhi)
    - canonical crop/disease/symptom codes stay unchanged in the database
    - the expert verification note is internal metadata and is NEVER copied
      into the farmer notification message
    - a separate farmer_instruction field may be supplied by the reviewer;
      that instruction is intentionally included in the Punjabi notification
    """

    CROP_PUNJABI = {
        "cotton": "کپاس",
        "rice": "دھان",
    }

    DISEASE_PUNJABI = {
        "bacterial_blight": "بیکٹیریا والی جھلس بیماری",
        "curl_virus": "پتیاں دے مڑن والی وائرس بیماری",
        "fusarium_wilt": "فیوزیریم مرجھاؤ",
        "blast": "بلاسٹ بیماری",
        "brown_spot": "بھورے دھبیاں دی بیماری",
        "healthy": "تندرست فصل",
    }

    SYMPTOM_PUNJABI = {
        "LEAF_YELLOWING": "پتے پیلے ہونا",
        "LEAF_CURLING": "پتے مڑنا",
        "LEAF_BROWN_SPOTS": "پتیاں اُتے بھورے دھبے",
        "LEAF_BLACK_SPOTS": "پتیاں اُتے کالے دھبے",
        "LEAF_WHITE_SPOTS": "پتیاں اُتے سفید دھبے",
        "LEAF_LESIONS": "پتیاں اُتے زخم یا خراب حصے",
        "LEAF_WATER_SOAKED_LESIONS": "پتیاں اُتے پانی ورگے گیلے زخم",
        "LEAF_SPINDLE_LESIONS": "پتیاں اُتے تکلے ورگے لمبے زخم",
        "LEAF_STREAKS": "پتیاں اُتے لمیاں لکیراں",
        "LEAF_EDGE_DRYING": "پتیاں دے کنارے سُکنا",
        "LEAF_TIP_DRYING": "پتیاں دے سرے سُکنا",
        "LEAF_DRYING": "پتے سُکنا",
        "LEAF_WILTING": "پتے مرجھانا",
        "LEAF_DISCOLORATION": "پتیاں دا رنگ بدلنا",
        "LEAF_HOLES": "پتیاں وچ سوراخ یا کھادھا ہویا حصہ",
        "STEM_DARKENING": "تنا کالا یا گہرا ہونا",
        "STEM_LESIONS": "تنے اُتے زخم",
        "STEM_WEAKENING": "تنا کمزور ہونا",
        "STEM_ROTTING": "تنا گلنا",
        "STEM_BREAKING": "تنا ٹٹنا یا پودا ڈِگنا",
        "PLANT_WILTING": "پورا پودا مرجھانا",
        "PLANT_DRYING": "پورا پودا سُکنا",
        "PLANT_YELLOWING": "پورا پودا پیلا ہونا",
        "PLANT_DISCOLORATION": "پورے پودے دا رنگ بدلنا",
        "STUNTED_GROWTH": "پودے دی بڑھوتری رکنا",
        "POOR_GROWTH": "پودے دی کمزور بڑھوتری",
        "PLANT_DEATH": "پودا مر جانا",
        "ROOT_DARKENING": "جڑاں دا رنگ گہرا ہونا",
        "ROOT_ROTTING": "جڑاں گلنا",
        "ROOT_DAMAGE": "جڑاں نوں نقصان",
        "BOLL_SPOTS": "ٹینڈیاں اُتے دھبے",
        "BOLL_ROTTING": "ٹینڈیاں گلنا",
        "BOLL_DAMAGE": "ٹینڈیاں نوں نقصان",
        "BOLL_DROP": "ٹینڈیاں وقت توں پہلاں ڈِگنا",
        "BOLL_OPENING_FAILURE": "ٹینڈیاں دا نہ کھلنا",
        "PANICLE_DISCOLORATION": "بالیاں دا رنگ بدلنا",
        "PANICLE_DRYING": "بالیاں سُکنا",
        "PANICLE_POOR_FILLING": "بالیاں وچ دانے ٹھیک نہ بھرنا",
        "GRAIN_DISCOLORATION": "دانیاں دا رنگ بدلنا",
        "GRAIN_DAMAGE": "دانیاں نوں نقصان",
        "OTHERS_MAP": "ہور غیر معمولی علامت",
    }

    def __init__(self) -> None:
        from app.config import get_settings

        self.settings = get_settings()
        self.devices = DeviceRepository()
        self.notifications = NotificationRepository()

    @classmethod
    def _crop_punjabi(cls, crop: str) -> str:
        return cls.CROP_PUNJABI.get((crop or "").lower(), "فصل")

    @classmethod
    def _disease_punjabi(cls, disease: str | None) -> str | None:
        if not disease:
            return None
        return cls.DISEASE_PUNJABI.get(disease.lower())

    @classmethod
    def _symptoms_punjabi(cls, alert: Alert) -> list[str]:
        values: list[str] = []
        for raw_code in alert.primary_symptom_codes or []:
            code = str(raw_code)
            label = cls.SYMPTOM_PUNJABI.get(code)
            if label and code != "OTHERS_MAP" and label not in values:
                values.append(label)
        return values[:4]

    @classmethod
    def _problem_punjabi(cls, alert: Alert) -> str:
        disease = cls._disease_punjabi(alert.primary_disease)
        if disease:
            return disease

        symptoms = cls._symptoms_punjabi(alert)
        if symptoms:
            return "، ".join(symptoms[:2])

        return "فصل دی بیماری یا غیر معمولی مسئلہ"

    def eligible_devices(
        self,
        db: Session,
        alert: Alert,
    ) -> list[tuple[RegisteredDevice, float]]:
        matched: list[tuple[RegisteredDevice, float]] = []
        for device in self.devices.active_with_location(db):
            crops = {str(c).lower() for c in (device.crops or [])}
            if alert.crop.lower() not in crops:
                continue

            distance = OutbreakService.distance_km(
                alert.center_latitude,
                alert.center_longitude,
                float(device.latitude),
                float(device.longitude),
            )
            # Do not reuse the outbreak-linking radius for delivery. Nearby
            # farmer notifications have their own configurable radius.
            if distance <= self.settings.notification_radius_km:
                matched.append((device, distance))

        return sorted(matched, key=lambda item: item[1])

    def farmer_message(self, alert: Alert, distance: float) -> tuple[str, str]:
        """Return Punjabi Shahmukhi title and message.

        ``verification_note`` remains private/internal. ``farmer_instruction``
        is an explicit reviewer-authored farmer-facing field and is therefore
        appended to the notification when present.
        """
        crop = self._crop_punjabi(alert.crop)
        problem = self._problem_punjabi(alert)
        symptoms = self._symptoms_punjabi(alert)

        title = "فصل دی بیماری دا تصدیق شدہ الرٹ"

        parts = [
            (
                f"الرٹ دی حالت: تصدیق شدہ۔ تہاڈے علاقے دے نیڑے {crop} دی فصل وچ "
                f"{problem} دی تصدیق ہوئی اے۔ ایہ متاثرہ علاقہ تہاڈی رجسٹرڈ جگہ توں "
                f"لگ بھگ {distance:.1f} کلومیٹر دور اے۔"
            )
        ]

        if symptoms:
            parts.append(f"عام علامتاں: {'، '.join(symptoms)}۔")

        instruction = (getattr(alert, "farmer_instruction", None) or "").strip()
        if instruction:
            parts.append(f"زرعی ماہر دی ہدایت: {instruction}")
        else:
            parts.append(
                "اپنی فصل دا معائنہ کرو، تے جے ایہ علامتاں نظر آون تے "
                "AI Fasal Shield تے رپورٹ جمع کرو۔ علاج یا سپرے دی رہنمائی لئی "
                "زرعی ماہر نال رابطہ کرو۔"
            )

        return title, " ".join(parts)

    def dispatch_confirmed_alert(self, db: Session, alert: Alert) -> int:
        if alert.alert_level != "RED" or alert.status != "confirmed":
            return 0

        created = 0
        for device, distance in self.eligible_devices(db, alert):
            title, punjabi_message = self.farmer_message(alert, distance)
            existing = self.notifications.get_for_alert_device(
                db,
                alert.alert_id,
                device.device_id,
            )

            if existing:
                # Re-confirming/editing an alert must not duplicate notifications,
                # but reviewer instruction changes should reach the farmer.
                changed = (
                    existing.title != title
                    or existing.message != punjabi_message
                    or existing.message_local != punjabi_message
                    or abs(float(existing.distance_km) - round(distance, 3)) > 1e-9
                )
                existing.title = title
                existing.message = punjabi_message
                existing.message_local = punjabi_message
                existing.language = "punjabi"
                existing.distance_km = round(distance, 3)
                if changed:
                    existing.status = "unread"
                    existing.read_at = None
                self.notifications.save(db, existing)
                continue

            row = Notification(
                notification_id=f"NTF-{uuid4().hex[:12].upper()}",
                alert_id=alert.alert_id,
                device_id=device.device_id,
                crop=alert.crop,
                # All farmer-facing text is Punjabi for the prototype.
                title=title,
                message=punjabi_message,
                message_local=punjabi_message,
                language="punjabi",
                distance_km=round(distance, 3),
                status="unread",
            )
            self.notifications.save(db, row)
            created += 1

        return created
