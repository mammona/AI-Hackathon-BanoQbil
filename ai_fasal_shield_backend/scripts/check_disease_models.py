from app.services.disease_model_service import DiseaseModelService


def main() -> None:
    service = DiseaseModelService()
    print("AI Fasal Shield disease model configuration")
    print("=" * 60)
    print("Routing source: API selected_crop (no SigLIP)\n")

    for crop in ("cotton", "rice"):
        path = service._model_path(crop)
        print(crop.upper())
        print(f"  model   : {path}")
        print(f"  exists  : {path.exists()}")
        try:
            labels = service.labels_for_crop(crop)
            print(f"  labels  : {labels}")
            print(f"  healthy : {service.has_healthy_class(crop)}")
            if not path.exists():
                print("  load    : skipped (copy the .pt file first)")
            else:
                info = service.model_info(crop)
                print(f"  load    : OK")
                print(f"  arch    : {info['architecture']}")
        except Exception as exc:
            print(f"  ERROR   : {exc}")

        if crop == "rice":
            print("  note    : rice mapping has no healthy class")
        print()


if __name__ == "__main__":
    main()
