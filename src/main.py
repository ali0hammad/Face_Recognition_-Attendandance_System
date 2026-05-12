import customtkinter as ctk
from tkinter import filedialog
import cv2
import threading
import copy
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

        self.tabview = ctk.CTkTabview(self.right_frame)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        self.tab_attendance = self.tabview.add("Attendance Mode")
        self.tab_admin = self.tabview.add("Admin Panel")

        self.setup_attendance_tab()
        self.setup_admin_tab()

        # Footer Signature
        self.footer = ctk.CTkLabel(self, text="Ali Hammad // 2025-CE-45", font=ctk.CTkFont(size=10, slant="italic"), text_color="gray")
        self.footer.grid(row=1, column=1, sticky="se", padx=10, pady=5)

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

    def setup_attendance_tab(self):
        self.attendance_info = ctk.CTkLabel(self.tab_attendance, text="Please stand in front of the camera and blink to mark attendance.", font=ctk.CTkFont(size=14))
        self.attendance_info.pack(pady=20)

    def setup_admin_tab(self):
        # Configure layout for symmetrical Admin Panel
        self.tab_admin.grid_columnconfigure(0, weight=1)
        self.tab_admin.grid_rowconfigure(0, weight=0) # Reg
        self.tab_admin.grid_rowconfigure(1, weight=1) # Directory

        # 1. Registration Frame (Top)
        self.reg_frame = ctk.CTkFrame(self.tab_admin)
        self.reg_frame.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="nsew")

        self.reg_title = ctk.CTkLabel(self.reg_frame, text="Register New Student", font=ctk.CTkFont(size=16, weight="bold"))
        self.reg_title.grid(row=0, column=0, columnspan=3, pady=5)

        self.name_entry = ctk.CTkEntry(self.reg_frame, placeholder_text="Student Name")
        self.name_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.roll_entry = ctk.CTkEntry(self.reg_frame, placeholder_text="Roll Number")
        self.roll_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.capture_btn = ctk.CTkButton(self.reg_frame, text="Capture & Register", command=self.register_student)
        self.capture_btn.grid(row=1, column=2, padx=5, pady=5)

        self.reg_status_label = ctk.CTkLabel(self.reg_frame, text="")
        self.reg_status_label.grid(row=2, column=0, columnspan=3, pady=2)

        # 2. Bottom section split into Student Directory and Attendance Export
        self.bottom_frame = ctk.CTkFrame(self.tab_admin, fg_color="transparent")
        self.bottom_frame.grid(row=1, column=0, pady=5, padx=10, sticky="nsew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(1, weight=1)
        self.bottom_frame.grid_rowconfigure(0, weight=1)

        # 2a. Student Directory
        self.dir_frame = ctk.CTkFrame(self.bottom_frame)
        self.dir_frame.grid(row=0, column=0, padx=(0, 5), sticky="nsew")

        self.dir_title = ctk.CTkLabel(self.dir_frame, text="Student Directory", font=ctk.CTkFont(size=16, weight="bold"))
        self.dir_title.pack(pady=5)

        # Add scrollable frame for students
        self.student_list_frame = ctk.CTkScrollableFrame(self.dir_frame)
        self.student_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.refresh_directory()

        # 2b. Attendance Export Directory
        self.export_frame = ctk.CTkFrame(self.bottom_frame)
        self.export_frame.grid(row=0, column=1, padx=(5, 0), sticky="nsew")

        self.export_title = ctk.CTkLabel(self.export_frame, text="Attendance & Exports", font=ctk.CTkFont(size=16, weight="bold"))
        self.export_title.pack(pady=5)

        # Folder Selection
        self.export_dir = ""
        self.folder_btn = ctk.CTkButton(self.export_frame, text="Select Export Folder", command=self.select_export_folder)
        self.folder_btn.pack(pady=10)

        self.folder_label = ctk.CTkLabel(self.export_frame, text="No folder selected", text_color="gray", wraplength=180)
        self.folder_label.pack(pady=5)

        self.export_students_btn = ctk.CTkButton(self.export_frame, text="Export Students CSV", command=self.export_students)
        self.export_students_btn.pack(pady=10)

        self.export_attendance_btn = ctk.CTkButton(self.export_frame, text="Export Attendance CSV", command=self.export_attendance)
        self.export_attendance_btn.pack(pady=10)

        self.export_status_label = ctk.CTkLabel(self.export_frame, text="")
        self.export_status_label.pack(pady=5)

    def select_export_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.export_dir = folder
            self.folder_label.configure(text=folder)
            self.export_status_label.configure(text="Folder updated.", text_color="green")

    def refresh_directory(self):
        # Clear existing widgets
        for widget in self.student_list_frame.winfo_children():
            widget.destroy()

        for student in self.known_students:
            row_frame = ctk.CTkFrame(self.student_list_frame)
            row_frame.pack(fill="x", pady=2)

            lbl = ctk.CTkLabel(row_frame, text=f"{student['roll_no']} - {student['name']}", anchor="w")
            lbl.pack(side="left", padx=5, expand=True, fill="x")

            edit_btn = ctk.CTkButton(row_frame, text="Edit", width=40,
                                     command=lambda s=student: self.edit_student_ui(s))
            edit_btn.pack(side="right", padx=5)

            del_btn = ctk.CTkButton(row_frame, text="Del", width=40, fg_color="red", hover_color="darkred",
                                    command=lambda r=student['roll_no']: self.delete_student_ui(r))
            del_btn.pack(side="right", padx=5)

    def edit_student_ui(self, student):
        dialog = ctk.CTkInputDialog(text=f"Enter new Name for {student['roll_no']} (leave blank to cancel):", title="Edit Student")
        new_name = dialog.get_input()
        if new_name:
            success, msg = database.update_student(student['roll_no'], student['roll_no'], new_name)
            if success:
                self.known_students = database.get_all_students()
                self.refresh_directory()
                self.auto_sync_csv()
                self.reg_status_label.configure(text=f"Student {student['roll_no']} updated.", text_color="green")
            else:
                self.reg_status_label.configure(text=msg, text_color="red")

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
        if self.export_dir:
            self.export_students()



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
            if self.current_frame is not None and self.tabview.get() == "Attendance Mode":
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

            if self.tabview.get() == "Attendance Mode" and not in_cooldown:
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

                # Refresh UI and Sync
                self.refresh_directory()
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
        if not hasattr(self, 'export_dir') or not self.export_dir:
            self.export_status_label.configure(text="Please select a folder first.", text_color="orange")
            return

        students = database.get_all_students()
        filename = f"{self.export_dir}/students_list_{datetime.now().strftime('%Y%m%d')}.csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll No', 'Name'])
                for s in students:
                    writer.writerow([s['roll_no'], s['name']])
            self.export_status_label.configure(text=f"Exported to {filename.split('/')[-1]}", text_color="green")
        except Exception as e:
            self.export_status_label.configure(text=f"Export failed: {str(e)}", text_color="red")

    def export_attendance(self):
        if not hasattr(self, 'export_dir') or not self.export_dir:
            self.export_status_label.configure(text="Please select a folder first.", text_color="orange")
            return

        logs = database.get_attendance_logs()
        filename = f"{self.export_dir}/attendance_logs_{datetime.now().strftime('%Y%m%d')}.csv"

        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Roll No', 'Name', 'Date', 'Time', 'Status'])
                for log in logs:
                    writer.writerow(log)
            self.export_status_label.configure(text=f"Exported to {filename.split('/')[-1]}", text_color="green")
        except Exception as e:
            self.export_status_label.configure(text=f"Export failed: {str(e)}", text_color="red")

if __name__ == "__main__":
    database.init_db()
    app = AttendanceSystem()
    app.mainloop()
