import customtkinter as ctk
import cv2
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

        # Left Frame for Camera & Status
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.video_label = ctk.CTkLabel(self.left_frame, text="")
        self.video_label.pack(pady=10, expand=True)

        self.status_label = ctk.CTkLabel(self.left_frame, text="System Ready", font=ctk.CTkFont(size=20, weight="bold"))
        self.status_label.pack(pady=10)

        # Right Frame for Tabview
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.tabview = ctk.CTkTabview(self.right_frame)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_attendance = self.tabview.add("Attendance Mode")
        self.tab_admin = self.tabview.add("Admin Panel")

        self.setup_attendance_tab()
        self.setup_admin_tab()

        # Camera Setup
        self.cap = None
        self.is_camera_running = False
        self.cooldown_until = None

        # Switch to attendance mode by default and start camera
        self.tabview.set("Attendance Mode")
        self.start_camera()

    def setup_attendance_tab(self):
        self.attendance_info = ctk.CTkLabel(self.tab_attendance, text="Please stand in front of the camera and blink to mark attendance.", font=ctk.CTkFont(size=14))
        self.attendance_info.pack(pady=20)

    def setup_admin_tab(self):
        # Registration Frame
        self.reg_frame = ctk.CTkFrame(self.tab_admin)
        self.reg_frame.pack(pady=20, padx=20, fill="x")

        self.reg_title = ctk.CTkLabel(self.reg_frame, text="Register New Student", font=ctk.CTkFont(size=18, weight="bold"))
        self.reg_title.grid(row=0, column=0, columnspan=2, pady=10)

        self.name_entry = ctk.CTkEntry(self.reg_frame, placeholder_text="Student Name")
        self.name_entry.grid(row=1, column=0, padx=10, pady=10)

        self.roll_entry = ctk.CTkEntry(self.reg_frame, placeholder_text="Roll Number")
        self.roll_entry.grid(row=1, column=1, padx=10, pady=10)

        self.capture_btn = ctk.CTkButton(self.reg_frame, text="Capture & Register", command=self.register_student)
        self.capture_btn.grid(row=2, column=0, columnspan=2, pady=10)

        self.reg_status_label = ctk.CTkLabel(self.reg_frame, text="")
        self.reg_status_label.grid(row=3, column=0, columnspan=2, pady=5)

        # Export Frame
        self.export_frame = ctk.CTkFrame(self.tab_admin)
        self.export_frame.pack(pady=20, padx=20, fill="x")

        self.export_title = ctk.CTkLabel(self.export_frame, text="Export Data", font=ctk.CTkFont(size=18, weight="bold"))
        self.export_title.grid(row=0, column=0, columnspan=2, pady=10)

        self.export_students_btn = ctk.CTkButton(self.export_frame, text="Export Students List", command=self.export_students)
        self.export_students_btn.grid(row=1, column=0, padx=10, pady=10)

        self.export_attendance_btn = ctk.CTkButton(self.export_frame, text="Export Attendance Logs", command=self.export_attendance)
        self.export_attendance_btn.grid(row=1, column=1, padx=10, pady=10)

        self.export_status_label = ctk.CTkLabel(self.export_frame, text="")
        self.export_status_label.grid(row=2, column=0, columnspan=2, pady=5)


    def start_camera(self):
        if not self.is_camera_running:
            self.cap = cv2.VideoCapture(0)
            self.is_camera_running = True
            self.update_frame()

    def stop_camera(self):
        if self.is_camera_running:
            self.is_camera_running = False
            if self.cap:
                self.cap.release()

    def update_frame(self):
        if not self.is_camera_running:
            return

        ret, frame = self.cap.read()
        if ret:
            # Check if we are in cooldown
            in_cooldown = False
            if self.cooldown_until:
                if datetime.now() < self.cooldown_until:
                    in_cooldown = True
                else:
                    self.cooldown_until = None
                    self.status_label.configure(text="System Ready", text_color="white")

            # Process frame for attendance if we are in Attendance tab and not in cooldown
            if self.tabview.get() == "Attendance Mode" and not in_cooldown:
                processed_frame, recognized_student, status_message, has_blinked = face_utils.process_frame_for_attendance(
                    frame, self.known_encodings, self.known_students
                )
                self.status_label.configure(text=status_message)

                if has_blinked and recognized_student:
                    self.mark_attendance_for_student(recognized_student)
                elif has_blinked and not recognized_student:
                    # Blinked but not recognized
                    self.status_label.configure(text="Unknown Face", text_color="red")
                    self.play_sound(success=False)
                    from datetime import timedelta
                    self.cooldown_until = datetime.now() + timedelta(seconds=2)
            else:
                processed_frame = frame

            # Convert to PhotoImage for Tkinter
            rgb_image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)

            # Resize for UI
            pil_image = pil_image.resize((640, 480), Image.Resampling.LANCZOS)
            photo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(640, 480))

            self.video_label.configure(image=photo_image)
            self.video_label.image = photo_image

        self.after(10, self.update_frame)

    def mark_attendance_for_student(self, student):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        # Simple late arrival logic: past 9:00 AM is late
        is_late = now.hour >= 9
        status = "Late" if is_late else "Present"

        success, msg = database.mark_attendance(student['roll_no'], date_str, time_str, status)

        if success:
            self.status_label.configure(text=f"Attendance Marked: {student['name']} ({status})", text_color="green" if not is_late else "orange")
            self.play_sound(success=True)
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
        filename = f"students_list_{datetime.now().strftime('%Y%m%d')}.csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll No', 'Name'])
                for s in students:
                    writer.writerow([s['roll_no'], s['name']])
            self.export_status_label.configure(text=f"Exported to {filename}", text_color="green")
        except Exception as e:
            self.export_status_label.configure(text=f"Export failed: {str(e)}", text_color="red")

    def export_attendance(self):
        logs = database.get_attendance_logs()
        filename = f"attendance_logs_{datetime.now().strftime('%Y%m%d')}.csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll No', 'Name', 'Date', 'Time', 'Status'])
                for log in logs:
                    writer.writerow(log)
            self.export_status_label.configure(text=f"Exported to {filename}", text_color="green")
        except Exception as e:
            self.export_status_label.configure(text=f"Export failed: {str(e)}", text_color="red")

if __name__ == "__main__":
    database.init_db()
    app = AttendanceSystem()
    app.mainloop()
