# Fasal Guard Mobile

A Flutter-based mobile application for crop disease detection and reporting. Fasal Guard helps farmers identify crop diseases through image analysis and voice-based symptom descriptions.

## Features

- **Crop Selection**: Choose from supported crops (Cotton, Rice, Wheat)
- **Image Capture & Validation**: Capture crop images with built-in validation
- **Voice Input**: Speech-to-text support for symptom descriptions (Hindi/Urdu)
- **Disease Detection**: AI-powered disease identification
- **Report Management**: View and manage submitted reports
- **Notifications**: Receive alerts and updates

## ASR Model (Auto-Download)

The app uses a Sherpa-ONNX based speech recognition model for voice input. The model file (`model.int8.onnx`, ~348 MB) is **not included in this repository** due to size constraints.

**The model will be automatically downloaded** on first launch when the voice input feature is used. The app handles this transparently — no manual intervention required.

### Manual Model Download (Optional)

If you need to pre-download the model for offline use or testing:

1. Place the model file at: `assets/asr_model/model.int8.onnx`
2. Place the tokens file at: `assets/asr_model/tokens.txt`

The model can be obtained from the Sherpa-ONNX model zoo or your project's model repository.

## Getting Started

### Prerequisites

- Flutter SDK (3.x recommended)
- Android Studio / Xcode for mobile development
- A physical device or emulator

### Setup

```bash
# Clone the repository
git clone https://github.com/mammona/AI-Hackathon-BanoQbil.git
cd fasal_guard_mobile

# Get Flutter dependencies
flutter pub get

# Run the app
flutter run
```

### Backend Configuration

The app communicates with a backend server for:
- Device registration
- Report submission
- Image upload (OSS)

Update `lib/config/api_config.dart` and `lib/config/remote_config.dart` with your backend URLs.

## Project Structure

```
lib/
├── config/          # App configuration, API endpoints, questions
├── models/          # Data models (FarmerReport, Notification, etc.)
├── screens/         # UI screens
├── services/        # Business logic (API, audio, image, location, etc.)
├── widgets/         # Reusable UI components
└── main.dart        # App entry point
```

## Supported Crops

- **Cotton**: Bollworm, Aphids, Fusarium Wilt, etc.
- **Rice**: Blast, Brown Spot, etc.
- **Wheat**: Rust, etc.

## License

[Your License Here]
