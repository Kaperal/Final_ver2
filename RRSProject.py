import tkinter as tk
from tkinter import ttk, filedialog
import cv2
from PIL import Image, ImageTk


class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera Application")

        # Maximize the window
        self.root.state('zoomed')

        # Configure grid layout for window
        self.root.grid_columnconfigure(0, weight=4)  # More weight to the video frame
        self.root.grid_columnconfigure(1, weight=1)  # Less weight to the control panel
        self.root.grid_rowconfigure(0, weight=1)  # Full height usage for row 0

        # Video Frame (on the left)
        self.video_frame = tk.Label(self.root)
        self.video_frame.grid(row=0, column=0, sticky="nsew")  # Sticky to expand in all directions

        # Control Frame (on the right)
        control_frame = tk.Frame(self.root)
        control_frame.grid(row=0, column=1, sticky="ns")  # Only stretch vertically

        # Dropdown for selecting camera
        self.camera_list = ttk.Combobox(control_frame, state="readonly", values=self.get_camera_list())
        self.camera_list.current(0)
        self.camera_list.pack(pady=10, padx=10)

        # Start button
        self.start_button = tk.Button(control_frame, text="Start Camera", command=self.start_camera)
        self.start_button.pack(pady=10)

        # Upload button
        self.upload_button = tk.Button(control_frame, text="Upload Picture", command=self.upload_image)
        self.upload_button.pack(pady=10)

        # Stop button
        self.stop_button = tk.Button(control_frame, text="Stop Camera", state="disabled", command=self.stop_camera)
        self.stop_button.pack(pady=10)

        # Crop button
        self.crop_button = tk.Button(control_frame, text="Crop Image", command=self.crop_image)
        self.crop_button.pack(pady=10)

        # Variables
        self.cap = None
        self.running = False
        self.image = None
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.crop_area = None

        # Bind mouse events for cropping
        self.video_frame.bind("<ButtonPress-1>", self.on_button_press)
        self.video_frame.bind("<B1-Motion>", self.on_mouse_drag)
        self.video_frame.bind("<ButtonRelease-1>", self.on_button_release)

    def get_camera_list(self):
        return ["Camera 0", "Camera 1", "Camera 2", "Camera 3"]

    def start_camera(self):
        if not self.running:
            self.running = True
            self.start_button.config(state="disabled")
            self.upload_button.config(state="disabled")
            self.stop_button.config(state="normal")

            camera_index = self.camera_list.current()
            self.cap = cv2.VideoCapture(camera_index)
            self.show_frame()

    def show_frame(self):
        if self.running:
            ret, frame = self.cap.read()
            if ret:
                # Resize the frame to fit the window size
                window_width = self.video_frame.winfo_width()
                window_height = self.video_frame.winfo_height()

                # Convert the frame to RGB (OpenCV uses BGR by default)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Resize the frame to fit the video frame dimensions
                frame_resized = cv2.resize(frame, (window_width, window_height), interpolation=cv2.INTER_AREA)

                # Convert to ImageTk format for tkinter
                img = Image.fromarray(frame_resized)
                imgtk = ImageTk.PhotoImage(image=img)

                # Display the image in the label
                self.video_frame.imgtk = imgtk
                self.video_frame.configure(image=imgtk)

            # Call this function again after 10ms
            self.root.after(10, self.show_frame)

    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if file_path:
            self.display_image(file_path)

    def display_image(self, file_path):
        # Stop the camera if it's running
        if self.running:
            self.stop_camera()

        # Load and display the image
        self.image = Image.open(file_path)
        img_resized = self.image.resize((self.video_frame.winfo_width(), self.video_frame.winfo_height()),
                                        Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img_resized)
        self.video_frame.imgtk = imgtk
        self.video_frame.configure(image=imgtk)

    def stop_camera(self):
        if self.running:
            self.running = False
            self.start_button.config(state="normal")
            self.upload_button.config(state="normal")
            self.stop_button.config(state="disabled")

            if self.cap is not None:
                self.cap.release()
                self.cap = None

            # Clear the video frame
            self.video_frame.config(image='')

    def on_button_press(self, event):
        # Start the selection rectangle
        self.start_x = event.x
        self.start_y = event.y
        self.rect_id = self.video_frame.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y,
                                                         outline='red')

    def on_mouse_drag(self, event):
        # Update the selection rectangle while dragging
        cur_x, cur_y = event.x, event.y
        self.video_frame.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        # Finalize the selection
        end_x, end_y = event.x, event.y
        self.crop_area = (self.start_x, self.start_y, end_x, end_y)

    def crop_image(self):
        if self.image and self.crop_area:
            # Perform cropping
            crop_box = (
                int(self.crop_area[0] * (self.image.width / self.video_frame.winfo_width())),
                int(self.crop_area[1] * (self.image.height / self.video_frame.winfo_height())),
                int(self.crop_area[2] * (self.image.width / self.video_frame.winfo_width())),
                int(self.crop_area[3] * (self.image.height / self.video_frame.winfo_height()))
            )
            cropped_image = self.image.crop(crop_box)

            # Display the cropped image
            cropped_resized = cropped_image.resize((self.video_frame.winfo_width(), self.video_frame.winfo_height()),
                                                   Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=cropped_resized)
            self.video_frame.imgtk = imgtk
            self.video_frame.configure(image=imgtk)


if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()