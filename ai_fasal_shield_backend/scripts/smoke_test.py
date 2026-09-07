import argparse
from pathlib import Path
import httpx

parser = argparse.ArgumentParser()
parser.add_argument("image", type=Path)
parser.add_argument("--crop", choices=["cotton", "rice"], default="cotton")
parser.add_argument("--url", default="http://127.0.0.1:8000")
args = parser.parse_args()

with args.image.open("rb") as f:
    response = httpx.post(
        f"{args.url}/api/v1/reports/process",
        data={
            "report_id": "SMOKE-001",
            "selected_crop": args.crop,
            "answer_1": "پتے مڑ رہے ہیں اور پیلے ہو رہے ہیں",
            "answer_2": "تین دن پہلے شروع ہوا",
            "answer_3": "تقریباً آدھا ایکڑ متاثر ہے",
            "answer_4": "مسئلہ پھیل رہا ہے",
            "latitude": "31.5204",
            "longitude": "74.3587",
            "timestamp": "2026-08-28T10:00:00+00:00",
        },
        files={"image": (args.image.name, f, "image/jpeg")},
        timeout=180,
    )
print(response.status_code)
print(response.text)
