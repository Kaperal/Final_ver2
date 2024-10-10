import tkinter as tk
from tkinter import Label, Button, Frame, ttk
import cv2
from PIL import Image, ImageTk
import datetime
import os
import csv
from ultralytics import YOLO
import math
import serial
import serial.tools.list_ports

# Desired display size
d_width = 1080
d_height = 720

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Camera")

        # Maximize the window
        self.root.state('zoomed')
        self.root.bind('<F11>', self.toggle_maximize)
        self.root.bind('<Escape>', self.exit_maximize)

        # Set up the left frame for video display
        self.left_frame = tk.Frame(root, width=d_width, height=d_height)
        self.left_frame.grid(row=0, column=0, padx=(1, 1), pady=(0, 0), sticky="nsew")

        # Set up the right frame for the control button, dropdown menu, and data display
        self.right_frame = tk.Frame(root, width=200, height=600)
        self.right_frame.grid(row=0, column=1, padx=(1, 1), pady=10, sticky="nsew")

        # Configure grid to expand the left frame more
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=3)  # Make the left frame take up more space
        self.root.grid_columnconfigure(1, weight=1)

        # Create a label to display the message
        self.message_label = Label(self.left_frame, text="Video display here", font=("Arial", 16))
        self.message_label.pack(side="top", pady=(10, 0))  # Adjust top padding

        # Create a label to display the video
        self.video_label = Label(self.left_frame)
        self.video_label.pack(expand=True, fill="both")  # No padding to minimize gap

        # Enumerate available cameras
        self.available_cameras = self.enumerate_cameras()

        # Create a dropdown menu to select the camera
        self.camera_var = tk.StringVar()
        self.camera_dropdown = ttk.Combobox(self.right_frame, textvariable=self.camera_var)
        self.camera_dropdown['values'] = self.available_cameras
        self.camera_dropdown.current(0)  # Set the default selection to the first camera
        self.camera_dropdown.pack(pady=10)

        # Create a label for the camera dropdown menu
        self.camera_label = Label(self.right_frame, text="Select camera")
        self.camera_label.pack(pady=5)

        # Enumerate available serial ports
        self.available_ports = self.enumerate_ports()

        # Create a dropdown menu to select the serial port
        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.right_frame, textvariable=self.port_var)
        self.port_dropdown['values'] = self.available_ports
        self.port_dropdown.current()  # Set the default selection to the first port
        self.port_dropdown.pack(pady=10)

        # Create a label for the port dropdown menu
        self.port_label = Label(self.right_frame, text="Select port")
        self.port_label.pack(pady=5)

        # Create a frame to hold the start/stop button and select port button
        self.button_frame = tk.Frame(self.right_frame)
        self.button_frame.pack(pady=20)

        # Create a button to start/stop the video
        self.start_button = Button(self.button_frame, text="Start Camera", command=self.toggle_camera)
        self.start_button.pack(side="left", padx=5)

        # Create a button to select the port
        self.port_button = Button(self.button_frame, text="Select Port", command=self.select_port)
        self.port_button.pack(side="left", padx=5)

        # Create another frame to hold the auto mode and test mode buttons
        self.mode_button_frame = tk.Frame(self.right_frame)
        self.mode_button_frame.pack(pady=20)

        # Create a button to activate texting system
        self.texting_system_button = Button(self.mode_button_frame, text="Activate Texting System", command=self.toggle_texting_system)
        self.texting_system_button.pack(side="left", padx=5)

        # Create a button for test mode
        self.test_mode_button = Button(self.mode_button_frame, text="Test mode", command=self.test_mode)
        self.test_mode_button.pack(side="left", padx=5)

        # Create a frame to hold the data display
        self.data_frame = Frame(self.right_frame)
        self.data_frame.pack(fill='both', expand=True, pady=(10, 0))

        # Create a canvas to make the data frame scrollable
        self.canvas = tk.Canvas(self.data_frame)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Add a scrollbar to the canvas
        self.scrollbar = ttk.Scrollbar(self.data_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")

        # Create a frame inside the canvas to hold the data labels
        self.scrollable_frame = Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Add the "Data here" label
        self.data_here_label = Label(self.right_frame, text="Data here")
        self.data_here_label.pack(pady=10)

        # Video capture control variables
        self.cap = None
        self.running = False

        # Initialize YOLO model
        self.model = YOLO("Model/best.pt")
        self.classNames = ['Assault_weapon', 'Blunt-objects', 'Handguns', 'Knives', 'SMG', 'Shotgun'
                          ]

        # Prepare for result saving
        self.prepare_results_folder()

        # Serial port control variables
        self.serial_inst = serial.Serial()
        self.selected_port = None

        # Texting system control variable
        self.text_system_active = False

        # Detection control variables
        self.detected_number = 0  # Moved here to persist across calls
        self.text_system_gate = 0  # Moved here to persist across calls

    def toggle_maximize(self, event=None):
        self.root.state('zoomed')

    def exit_maximize(self, event=None):
        self.root.state('normal')

    def enumerate_cameras(self):
        available = []
        for i in range(5):  # Try up to 5 indices for simplicity
            cap = cv2.VideoCapture(i)
            if cap.read()[0]:
                available.append(i)
                cap.release()
        return available

    def enumerate_ports(self):
        ports = serial.tools.list_ports.comports()
        return [str(port) for port in ports]

    def select_port(self):
        self.selected_port = self.port_var.get()
        self.serial_inst.port = self.selected_port.split()[0]
        self.serial_inst.baudrate = 9600
        if self.selected_port:
            self.serial_inst.port = self.selected_port.split()[0]
            self.serial_inst.baudrate = 9600
            try:
                self.serial_inst.open()
                self.serial_inst.flushInput()
                print(f"Selected port: {self.serial_inst.port}")
            except Exception as e:
                print(f"Error opening serial port: {e}")

    def toggle_camera(self):
        if self.running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        selected_camera = int(self.camera_var.get())
        self.cap = cv2.VideoCapture(selected_camera)  # Open the selected camera
        self.running = True
        self.start_button.config(text="Stop Camera")
        self.message_label.config(text="Video display here")
        self.video_loop()

    def stop_camera(self):
        self.running = False
        self.start_button.config(text="Start Camera")
        if self.cap:
            self.cap.release()
            self.cap = None
            self.video_label.config(image='')
            self.message_label.config(text="")  # Hide the message

    def toggle_texting_system(self):
        if self.text_system_active:
            self.texting_system_button.config(text="Activate Texting System")
        else:
            self.texting_system_button.config(text="Disable Texting System")
        self.text_system_active = not self.text_system_active

    def test_mode(self):
        if self.serial_inst.is_open:
            self.serial_inst.flushInput()
            self.serial_inst.write(b"Test")
            print("Test message sent to the Arduino.")

    def video_loop(self):
        if self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # Perform YOLO detection
                results = self.model(frame, stream=True, imgsz=640)

                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        # bounding box
                        x1, y1, x2, y2 = box.xyxy[0]
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # convert to int values
                        w = x2 - x1
                        h = y2 - y1
                        # put box in frame
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)

                        # confidence
                        confidence = math.ceil((box.conf[0] * 100)) / 100

                        # class name
                        cls = int(box.cls[0])
                        label = self.classNames[cls]

                        # put label on frame
                        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
                        #
                        # Increment the detected number
                        self.detected_number += 1
                        if self.detected_number > 3 and self.text_system_gate == 0 and self.text_system_active:
                            self.serial_inst.flushInput()
                            self.serial_inst.write(label.encode())  # Convert label to bytes
                            print("Message sent to the Arduino.")
                            self.text_system_gate = 1

                        # Log the object details to CSV
                        with open(self.csv_file_path, 'a', newline='') as csvfile:
                            csv_writer = csv.writer(csvfile)
                            if self.header == 0:
                                csv_writer.writerow(["Label", "X coordinate", "Y coordinate", "Confidence", "Time", "Frame Count"])
                                self.header = 1

                            # Scrollable list display
                            current_time = datetime.datetime.now().strftime("%H:%M:%S")
                            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                            data_type = label
                            accuracy = confidence
                            test_data = f"Time: {current_time}, Date: {current_date}, Type: {data_type}, Accuracy: {accuracy}"

                            # Create a label for the new data and add it to the scrollable frame
                            data_label = Label(self.scrollable_frame, text=test_data, anchor="w", justify="left")
                            data_label.pack(fill="x", padx=10, pady=2)
                            csv_writer.writerow([label, x1, y1, confidence, current_time, self.frame_count])

                # Resize the frame to the desired display size
                frame = cv2.resize(frame, (d_width, d_height))

                # Save the frame to the disk
                frame_path = os.path.join(self.pics_folder_path, f"frame_{self.frame_count}.jpg")
                cv2.imwrite(frame_path, frame)

                # Write the frame to the video file
                self.video_writer.write(frame)

                self.frame_count += 1

                # Convert the frame to ImageTk format
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                imgtk = ImageTk.PhotoImage(image=img)

                # Update the label with the new frame
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)

            # Call this method again after 10 ms
            self.root.after(10, self.video_loop)

    def prepare_results_folder(self):
        # Create a folder to save the results if it doesn't exist
        home_dir = os.path.expanduser("~")
        documents_dir = os.path.join(home_dir, "Documents")
        result_folder_path = os.path.join(documents_dir, 'results_Yolov8')
        os.makedirs(result_folder_path, exist_ok=True)

        # Create a sub-folder for the current run
        timestamp = datetime.datetime.now().strftime("%b_%d_%Y_%H_%M_%S")
        self.run_folder = os.path.join(result_folder_path, timestamp)
        os.makedirs(self.run_folder, exist_ok=True)

        # Path for CSV and pictures
        self.csv_file_path = os.path.join(self.run_folder, "detection_results.csv")
        self.pics_folder_path = os.path.join(self.run_folder, "frames")
        os.makedirs(self.pics_folder_path, exist_ok=True)

        # Initialize header flag and frame count
        self.header = 0
        self.frame_count = 0

        # Initialize VideoWriter
        video_path = os.path.join(self.run_folder, "output_video.avi")
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        self.video_writer = cv2.VideoWriter(video_path, fourcc, 20.0, (d_width, d_height))

    def __del__(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
        if self.serial_inst.is_open:
            self.serial_inst.close()
        if hasattr(self, 'video_writer') and self.video_writer.isOpened():
            self.video_writer.release()

# Create the main window
root = tk.Tk()
app = CCTVApp(root)
root.mainloop()
