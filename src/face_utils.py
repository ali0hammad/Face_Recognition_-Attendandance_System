import cv2
import face_recognition
import numpy as np

def calculate_ear(eye_landmarks):
    """
    Calculate the Eye Aspect Ratio (EAR) given 6 facial landmarks for an eye.
    The landmarks are ordered starting from the outer corner and moving clockwise.
    """
    # Vertical eye landmarks
    A = np.linalg.norm(np.array(eye_landmarks[1]) - np.array(eye_landmarks[5]))
    B = np.linalg.norm(np.array(eye_landmarks[2]) - np.array(eye_landmarks[4]))

    # Horizontal eye landmarks
    C = np.linalg.norm(np.array(eye_landmarks[0]) - np.array(eye_landmarks[3]))

    # Calculate EAR
    ear = (A + B) / (2.0 * C)
    return ear

def is_blinking(face_landmarks, ear_threshold=0.25):
    """
    Check if the person is blinking based on the EAR of both eyes.
    """
    left_eye = face_landmarks['left_eye']
    right_eye = face_landmarks['right_eye']

    left_ear = calculate_ear(left_eye)
    right_ear = calculate_ear(right_eye)

    avg_ear = (left_ear + right_ear) / 2.0

    return avg_ear < ear_threshold, avg_ear

def get_face_encoding(image_bgr):
    """
    Convert a BGR image (OpenCV format) to RGB and return the first face encoding found.
    Returns None if no face or multiple faces are found (to ensure accuracy for registration).
    """
    rgb_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image)

    if len(face_locations) != 1:
        return None, "Ensure exactly one face is in the frame."

    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

    if len(face_encodings) > 0:
        return face_encodings[0], "Success"
    return None, "Could not extract face encoding."

def process_frame_for_attendance(image_bgr, known_encodings, known_students, ear_threshold=0.25):
    """
    Process a single frame for attendance:
    1. Find all faces
    2. Check for blink (liveness)
    3. Recognize face if blinked
    4. Draw bounding boxes

    Returns:
        processed_image: Image with annotations
        recognized_student: Dict of student info if recognized and blinked, else None
        status_message: Info message about the current state
        blink_status: Boolean indicating if a blink was detected
    """
    rgb_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image)

    # Only process if we found exactly one face to avoid confusion
    if len(face_locations) == 0:
        return image_bgr, None, "No face detected.", False
    elif len(face_locations) > 1:
        # Still draw boxes but don't process attendance to avoid errors
        for (top, right, bottom, left) in face_locations:
            cv2.rectangle(image_bgr, (left, top), (right, bottom), (0, 255, 255), 2)
        return image_bgr, None, "Multiple faces detected. Please show only one.", False

    # Extract single face location
    top, right, bottom, left = face_locations[0]

    # Draw yellow bounding box around the face
    cv2.rectangle(image_bgr, (left, top), (right, bottom), (0, 255, 255), 2)

    # Get facial landmarks to check for blink
    face_landmarks_list = face_recognition.face_landmarks(rgb_image, face_locations)

    has_blinked = False
    ear_value = 0.0

    if len(face_landmarks_list) > 0:
        landmarks = face_landmarks_list[0]
        if 'left_eye' in landmarks and 'right_eye' in landmarks:
            has_blinked, ear_value = is_blinking(landmarks, ear_threshold)

            # Display EAR on screen for debugging/feedback
            cv2.putText(image_bgr, f"EAR: {ear_value:.2f}", (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    recognized_student = None
    status_message = "Please blink to verify liveness."

    if has_blinked:
        status_message = "Blink detected. Recognizing..."

        # Only compute encoding if a blink was detected (saves processing)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

        if len(face_encodings) > 0 and known_encodings:
            encoding_to_check = face_encodings[0]

            # Compare with known encodings
            matches = face_recognition.compare_faces(known_encodings, encoding_to_check, tolerance=0.5)
            face_distances = face_recognition.face_distance(known_encodings, encoding_to_check)

            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    recognized_student = known_students[best_match_index]
                    status_message = f"Recognized: {recognized_student['name']}"
                else:
                    status_message = "Unknown Face detected."

    return image_bgr, recognized_student, status_message, has_blinked
