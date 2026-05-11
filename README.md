# BLINK - Biometric Liveness & Identity Network Keeper

## Introduction
**BLINK** is a secure, standalone Python desktop application built to streamline and modernize attendance tracking. By replacing manual roll calls and ID swiping with instant facial recognition and anti-spoofing techniques, BLINK offers a reliable and user-friendly experience suitable for educational and corporate environments.

## How it works
The application leverages the user's webcam for continuous, real-time scanning:
- **Face Detection & Recognition**: Utilizing OpenCV and the `face_recognition` library, BLINK detects faces and verifies them against a database of registered identities using 128-dimensional encodings.
- **Liveness Detection**: To prevent spoofing via printed photos or screens, the system requires an active blink. It calculates the Eye Aspect Ratio (EAR) using `dlib` facial landmarks to confirm liveness.
- **Attendance Marking**: Upon successful liveness verification and identity matching, attendance is logged locally in an SQLite database with precision timestamps.
- **Admin Management**: An integrated admin panel allows for swift registration of new users and seamless exportation of attendance logs.

## Installation Procedure
Ensure Python 3 is installed on your system.

1. **Clone the repository** (or download the source):
   ```bash
   git clone <repository-url>
   cd src
   ```

2. **Install dependencies**:
   *(Note: Installing `dlib` and `face_recognition` may require CMake and a C++ compiler on your system.)*
   ```bash
   pip install setuptools==69.5.1
   pip install -r requirements.txt
   pip install git+https://github.com/ageitgey/face_recognition_models
   ```

## Basic Instructions
- **Launch the App**: Run `python main.py` from the `src` directory.
- **Register Users**: Navigate to the **Admin Panel**, enter the user details, look into the camera, and click **Capture & Register**.
- **Mark Attendance**: Switch to the **Attendance Mode** tab, stand in front of the camera, and blink once. A sound and on-screen status will confirm your attendance.
- **Export Data**: Use the **Admin Panel** to export user lists and daily attendance logs to CSV formats.
