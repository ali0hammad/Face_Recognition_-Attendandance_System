import customtkinter as ctk
import cv2
import threading
from PIL import Image, ImageTk
import database
import face_utils
from datetime import datetime
import csv
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AttendanceSystem(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Face Recognition Attendance System")
        self.geometry("1100x600")

        # Load students from DB
        self.known_students = database.get_all_students()
        self.known_encodings = [s['encoding'] for s in self.known_students]

        # Global UI Setup
        # Use grid layout to place camera on left and controls on right
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Left Frame for Camera & Status
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")

        self.video_label = ctk.CTkLabel(self.left_frame, text="")
        self.video_label.pack(pady=10, expand=True)

        self.status_label = ctk.CTkLabel(self.left_frame, text="System Ready", font=ctk.CTkFont(size=20, weight="bold"))
        self.status_label.pack(pady=10)

        # Right Frame for Tabview
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.active_tab = "Attendance Mode"
        self.tabview = ctk.CTkTabview(self.right_frame, command=self.on_tab_change)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_attendance = self.tabview.add("Attendance Mode")
        self.tab_admin = self.tabview.add("Admin Panel")

        self.setup_attendance_tab()
        self.setup_admin_tab()

        # Footer Signature Frame
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent", border_width=1, border_color="#3b82f6", corner_radius=6)
        self.footer_frame.grid(row=1, column=1, sticky="se", padx=10, pady=(0, 10))

        self.footer = ctk.CTkLabel(self.footer_frame, text="Ali Hammad // 2025-CE-45",
                                   font=ctk.CTkFont(size=12, weight="bold", slant="italic"),
                                   text_color="#60a5fa") # Distinct light blue
        self.footer.pack(padx=10, pady=2)

        # Camera Setup
        self.cap = None
        self.is_camera_running = False
        self.cooldown_until = None

        # Threading state
        self.current_frame = None
        self.processed_result = None  # (recognized_student, status_message, has_blinked, bounding_box)
        self.processing_thread = None

        # Switch to attendance mode by default and start camera
        self.tabview.set("Attendance Mode")
        self.start_camera()

    def on_tab_change(self):
        self.active_tab = self.tabview.get()

    def setup_attendance_tab(self):
        # Instructions
        self.attendance_info = ctk.CTkLabel(self.tab_attendance, text="Please look directly at the camera and blink to mark your attendance.", font=ctk.CTkFont(size=14))
        self.attendance_info.pack(pady=(20, 20))

    def setup_admin_tab(self):
        # Minimalist Admin Panel - Registration Only
        self.reg_frame = ctk.CTkFrame(self.tab_admin)
        self.reg_frame.pack(pady=50, padx=50, fill="both", expand=True)

        self.reg_title = ctk.CTkLabel(self.reg_frame, text="Register New Student", font=ctk.CTkFont(size=24, weight="bold"))
        self.reg_title.pack(pady=(30, 20))

        self.name_entry = ctk.CTkEntry(self.reg_frame, placeholder_text="Student Name", width=300)
        self.name_entry.pack(pady=10)

        self.roll_entry = ctk.CTkEntry(self.reg_frame, placeholder_text="Roll Number", width=300)
        self.roll_entry.pack(pady=10)

        self.capture_btn = ctk.CTkButton(self.reg_frame, text="Capture Face & Register", width=300, command=self.register_student)
        self.capture_btn.pack(pady=20)

        self.reg_status_label = ctk.CTkLabel(self.reg_frame, text="", font=ctk.CTkFont(size=14))
        self.reg_status_label.pack(pady=10)





    def delete_student_ui(self, roll_no):
        success, msg = database.delete_student(roll_no)
        if success:
            self.known_students = database.get_all_students()
            self.known_encodings = [s['encoding'] for s in self.known_students]
            self.refresh_directory()
            self.auto_sync_csv()
            self.reg_status_label.configure(text=f"Student {roll_no} deleted.", text_color="orange")
        else:
            self.reg_status_label.configure(text=msg, text_color="red")

    def auto_sync_csv(self):
        self.export_students()
        self.export_attendance()



    def start_camera(self):
        if not self.is_camera_running:
            self.cap = cv2.VideoCapture(0)
            self.is_camera_running = True

            # Start background processing thread
            self.processing_thread = threading.Thread(target=self.process_frame_background, daemon=True)
            self.processing_thread.start()

            self.update_frame_ui()

    def stop_camera(self):
        if self.is_camera_running:
            self.is_camera_running = False
            if self.cap:
                self.cap.release()

    def process_frame_background(self):
        while self.is_camera_running:
            if self.current_frame is not None and self.active_tab == "Attendance Mode":
                # Only process if we aren't in cooldown
                in_cooldown = False
                if self.cooldown_until and datetime.now() < self.cooldown_until:
                    in_cooldown = True

                if not in_cooldown:
                    # Grab a copy of the current frame so we don't mutate while UI reads it
                    frame_to_process = self.current_frame.copy()
                    _, recognized_student, status_message, has_blinked, bounding_box = face_utils.process_frame_for_attendance_threaded(
                        frame_to_process, self.known_encodings, self.known_students
                    )
                    self.processed_result = (recognized_student, status_message, has_blinked, bounding_box)
                else:
                    self.processed_result = None
            else:
                self.processed_result = None

            # Sleep a bit to prevent 100% CPU usage
            import time
            time.sleep(0.05)

    def update_frame_ui(self):
        if not self.is_camera_running:
            return

        ret, frame = self.cap.read()
        if ret:
            self.current_frame = frame
            display_frame = frame.copy()

            # Handle Cooldown
            in_cooldown = False
            if self.cooldown_until:
                if datetime.now() < self.cooldown_until:
                    in_cooldown = True
                else:
                    self.cooldown_until = None
                    self.status_label.configure(text="System Ready", text_color="white")

            if self.active_tab == "Attendance Mode" and not in_cooldown:
                # Apply the latest background processing results to the UI frame
                if self.processed_result:
                    recognized_student, status_message, has_blinked, bounding_box = self.processed_result

                    self.status_label.configure(text=status_message)

                    if bounding_box:
                        top, right, bottom, left = bounding_box
                        cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 255), 2)

                    if has_blinked and recognized_student:
                        self.mark_attendance_for_student(recognized_student)
                        self.processed_result = None # Clear result so we don't trigger twice
                    elif has_blinked and not recognized_student:
                        self.status_label.configure(text="Unknown Face", text_color="red")
                        self.play_sound(success=False)
                        from datetime import timedelta
                        self.cooldown_until = datetime.now() + timedelta(seconds=2)
                        self.processed_result = None

            # Convert to PhotoImage for Tkinter
            rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)

            # Resize for UI
            pil_image = pil_image.resize((640, 480), Image.Resampling.LANCZOS)
            photo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(640, 480))

            self.video_label.configure(image=photo_image)
            self.video_label.image = photo_image

        # Run at ~60 FPS (16ms) for buttery smooth UI, because heavy math is on background thread
        self.after(16, self.update_frame_ui)

    def mark_attendance_for_student(self, student):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")

        status = "Present"

        success, msg = database.mark_attendance(student['roll_no'], date_str, status)

        if success:
            self.status_label.configure(text=f"Attendance Marked: {student['name']} ({status})", text_color="green")
            self.play_sound(success=True)
            self.auto_sync_csv() # Also update export file seamlessly
        else:
            self.status_label.configure(text=f"Already Marked: {student['name']}", text_color="yellow")
            self.play_sound(success=True) # Or distinct sound for already marked

        # Set cooldown to avoid immediate rescanning and to allow user to read the message
        from datetime import timedelta
        self.cooldown_until = datetime.now() + timedelta(seconds=3)

    def play_sound(self, success):
        """Cross-platform beep using print if winsound is unavailable"""
        try:
            import winsound
            if success:
                winsound.Beep(1000, 200)  # Affirmative
            else:
                winsound.Beep(500, 500)   # Negative
        except ImportError:
            # Fallback for Linux/Mac
            if success:
                print('\a')
            else:
                print('\a\a')

    def register_student(self):
        name = self.name_entry.get()
        roll_no = self.roll_entry.get()

        if not name or not roll_no:
            self.reg_status_label.configure(text="Please enter both Name and Roll Number.", text_color="red")
            return

        ret, frame = self.cap.read()
        if not ret:
            self.reg_status_label.configure(text="Failed to capture from camera.", text_color="red")
            return

        encoding, msg = face_utils.get_face_encoding(frame)

        if encoding is not None:
            success, db_msg = database.add_student(roll_no, name, encoding)
            if success:
                self.reg_status_label.configure(text=db_msg, text_color="green")
                # Update local cache
                self.known_students = database.get_all_students()
                self.known_encodings = [s['encoding'] for s in self.known_students]

                # Auto-sync exports in background
                self.auto_sync_csv()

                # Clear fields
                self.name_entry.delete(0, 'end')
                self.roll_entry.delete(0, 'end')
            else:
                self.reg_status_label.configure(text=db_msg, text_color="red")
        else:
            self.reg_status_label.configure(text=msg, text_color="red")
            self.play_sound(success=False)

    def export_students(self):
        students = database.get_all_students()
        filename = "students_list.csv"
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll No', 'Name'])
                for s in students:
                    writer.writerow([s['roll_no'], s['name']])
        except Exception:
            pass

    def export_attendance(self):
        logs = database.get_attendance_logs()
        filename = "attendance_logs.csv"
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll No', 'Name', 'Date', 'Status'])
                for log in logs:
                    writer.writerow(log)
        except Exception:
            pass

if __name__ == "__main__":
    database.init_db()
    app = AttendanceSystem()
    app.mainloop()
