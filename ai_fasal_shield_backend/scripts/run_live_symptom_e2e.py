"""Run a real live API test through Qwen -> RAG -> SQLite -> outbreak -> RED.

Requirements:
- FastAPI running on http://127.0.0.1:8000
- Ollama running with qwen3:1.7b and qwen3-embedding:0.6b
- Qwen3 dedicated reranker available locally
- Prefer a clean database before running this script

This intentionally uses symptom-only reports so no disease-model image file is required.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--expert", default="Demo Agriculture Officer")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api = f"{base}/api/v1"

    with httpx.Client(timeout=180.0) as client:
        health = client.get(f"{base}/health")
        health.raise_for_status()
        print("Health:", health.json())

        summary = client.get(f"{api}/dashboard/summary")
        summary.raise_for_status()
        existing = int(summary.json().get("total_reports", 0))
        if existing != 0:
            raise SystemExit(
                f"Live E2E expects a clean database, but total_reports={existing}. "
                "Run: python -m scripts.reset_prototype_db, restart FastAPI, then retry."
            )

        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        device_id = "LIVE-E2E-FARMER-001"
        cases = [
            ("LIVE-E2E-CURL-001", 31.5204, 74.3587, "NO_ALERT"),
            ("LIVE-E2E-CURL-002", 31.5214, 74.3597, "MONITORING"),
            ("LIVE-E2E-CURL-003", 31.5224, 74.3607, "MONITORING"),
            ("LIVE-E2E-CURL-004", 31.5234, 74.3617, "AMBER"),
        ]

        last_alert_id = None
        for report_id, lat, lon, expected in cases:
            data = {
                "report_id": report_id,
                "device_id": device_id,
                "selected_crop": "cotton",
                "language": "punjabi",
                "answer_1": "پتے مڑ رہے نیں",
                "answer_2": "دو دن توں",
                "answer_3": "آدھا ایکڑ",
                "answer_4": "ہاں مسئلہ پھیل رہیا اے",
                "latitude": str(lat),
                "longitude": str(lon),
                "timestamp": timestamp,
            }
            response = client.post(f"{api}/reports/process", data=data)
            if response.status_code != 200:
                print(response.text)
                response.raise_for_status()
            body = response.json()
            outbreak = body["outbreak_assessment"]
            actual = outbreak.get("alert_level")
            codes = body.get("assessment", {}).get("symptom_codes", [])
            print(
                f"{report_id}: codes={codes} level={actual} "
                f"related={outbreak.get('related_report_count')} alert={outbreak.get('alert_id')}"
            )
            if "LEAF_CURLING" not in codes:
                raise SystemExit(
                    f"FAIL: {report_id} did not map to LEAF_CURLING. "
                    "Inspect Qwen extraction/reranker output before testing outbreak logic."
                )
            if actual != expected:
                raise SystemExit(f"FAIL: {report_id} expected {expected}, got {actual}")
            last_alert_id = outbreak.get("alert_id") or last_alert_id

        if not last_alert_id:
            raise SystemExit("FAIL: no Amber alert id was returned")

        verify = client.post(
            f"{api}/alerts/{last_alert_id}/verify",
            json={
                "decision": "confirmed",
                "expert_name": args.expert,
                "note": "Live E2E prototype verification.",
                "farmer_instruction": "اپنی فصل دا روزانہ معائنہ کرو تے نئی علامت نظر آوے تے رپورٹ جمع کرو۔",
            },
        )
        verify.raise_for_status()
        verified = verify.json()
        print("Verified alert:", verified)
        if verified.get("alert_level") != "RED" or verified.get("status") != "confirmed":
            raise SystemExit("FAIL: expert confirmation did not produce RED")

        device = client.get(f"{api}/devices/{device_id}")
        device.raise_for_status()
        print("Registered reporting device:", device.json())

        farmer_notifications = client.get(f"{api}/devices/{device_id}/notifications")
        farmer_notifications.raise_for_status()
        rows = farmer_notifications.json()
        if not rows:
            raise SystemExit("FAIL: RED alert did not create a notification for the reporting device")
        if "زرعی ماہر دی ہدایت:" not in rows[0].get("message", ""):
            raise SystemExit("FAIL: farmer instruction is missing from Punjabi notification")
        print("Farmer notification:", rows[0])

        final_summary = client.get(f"{api}/dashboard/summary")
        final_summary.raise_for_status()
        print("Final dashboard:", final_summary.json())
        print("PASS: live Qwen -> RAG -> SQL -> device registration -> outbreak -> expert RED -> Punjabi notification flow completed.")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as exc:
        print(f"HTTP failure: {exc}", file=sys.stderr)
        raise SystemExit(1)
