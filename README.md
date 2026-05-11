# Face Recognition Attendance System

## Introduction
The **Face Recognition Attendance System** is a standalone Python desktop application designed to streamline the process of marking attendance. It replaces manual roll calls and ID swiping with instant, secure facial recognition. This system is useful for schools, universities, and corporate environments where tracking attendance needs to be fast, reliable, and user-friendly.

It features a modern UI, SQLite database integration, cross-platform audio feedback, and basic liveness detection to prevent spoofing.

## How it works
The application uses the user's webcam to continuously scan for faces:
1. **Face Detection & Recognition**: Utilizing OpenCV and the `face_recognition` library, it detects a face in the frame and compares its 128-dimensional encoding against a database of known students.
2. **Liveness Detection**: To prevent spoofing (e.g., using a printed photo), the system requires the user to **blink**. It calculates the Eye Aspect Ratio (EAR) using `dlib` facial landmarks to ensure a real human is present.
3. **Attendance Marking**: Once a verified user blinks, their attendance is logged into a local SQLite database with a timestamp. If they arrive after 9:00 AM, they are marked as "Late".
4. **Admin Panel**: An administrator can use the dedicated tab to register new students (capturing their face instantly) and export attendance logs to CSV files.

## Installation Procedure
To run this application, you need Python 3 installed on your system.

1. **Clone the repository** (or download the source code).
2. **Navigate to the project directory**:
   ```bash
   cd src
   ```
3. **Install the required dependencies**:
   Make sure you have `setuptools` installed, as it is required by the face recognition models.
   ```bash
   pip install setuptools==69.5.1
   pip install -r requirements.txt
   pip install git+https://github.com/ageitgey/face_recognition_models
   ```
   *Note: Installing `dlib` and `face_recognition` may require CMake and a C++ compiler on your system.*

## Basic Instructions
1. **Starting the Application**:
   Run the main script from the `src` directory:
   ```bash
   python main.py
   ```
2. **Registering a New User**:
   - Click on the **Admin Panel** tab.
   - Enter the student's Name and Roll Number.
   - Look at the camera and click **Capture & Register**.
3. **Marking Attendance**:
   - Switch to the **Attendance Mode** tab.
   - Stand in front of the camera.
   - **Blink** your eyes once.
   - The system will beep and display a success message if you are recognized.
4. **Exporting Data**:
   - Go to the **Admin Panel**.
   - Click **Export Students List** or **Export Attendance Logs** to generate CSV files of your data.
