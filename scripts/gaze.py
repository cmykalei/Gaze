import cv2              # Camera capture and GUI
import mediapipe as mp  # Face and iris landmark detection
import numpy as np      # Math, arrays, and linear algebra
import tkinter as tk    # Dynamically get screen size
import csv              # For comma seperated values.
import os               # To make directories for logging.
import math             # Could delete, check first.

from config import Eye
from config import Nose
from config import Mouth
from config import State

def get_screen_dimensions():
    try:
        root = tk.Tk()
        root.withdraw() # Hides the window.
        full_width = root.winfo_screenwidth()
        full_height = root.winfo_screenheight()
        root.destroy()
        return full_width, full_height
    except Exception as e:
        print(f"Failed to get screen dimensions: {e}")
        return None, None

class Deltas:
    def __init__(self):
        self.pairs = {}
        self.deltas = {}

    def compute(self, pairs):
        self.pairs = pairs
        self.deltas = {}
        for name, (a, b) in pairs.items():
            a = np.array(a)
            b = np.array(b)
            if a.ndim > 1 or len(a) > 2:
                a = np.mean(a, axis=0)
            if b.ndim > 1 or len(b) > 2:
                b = np.mean(b, axis=0)
            self.deltas[name] = math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)
        return self.deltas

    def log(self, label: str, filename: str):
        header = ["label"] + list(self.deltas.keys())
        row = [label] + [f"{v:.2f}" for v in self.deltas.values()]
        file_path = f"logs/{filename}.csv"
        file_exists = os.path.isfile(file_path)
        with open(file_path, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(header)
            w.writerow(row)

    def draw(self, frame: np.ndarray, color, thickness):
        for name, (a, b) in self.pairs.items():
            a = tuple(map(int, a))
            b = tuple(map(int, b))
            cv2.line(frame, a, b, color, thickness)
            mx, my = int((a[0]+b[0])/2), int((a[1]+b[1])/2)
            cv2.putText(frame, f"{self.deltas[name]:.1f}", (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

def get_frame_cap(video: cv2.VideoCapture):
    if not isinstance(video, cv2.VideoCapture):
        raise TypeError("Parameter 'video' must be a cv2.VideoCapture object.")
    else:
        success, frame = video.read()
        if not success:
            print("Failed to grab frame from cv2.VideoCapture.")
            return None
        else:
            return frame

def detect_face(frame: np.ndarray, mesh: mp.solutions.face_mesh.FaceMesh):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    output = mesh.process(rgb)
    if not output.multi_face_landmarks:
        return None
    else:
        landmarks = output.multi_face_landmarks[0].landmark
        face = np.array([(lm.x, lm.y) for lm in landmarks])
        return face

def detect_iris(frame: np.ndarray, face: np.ndarray, iris) -> tuple[int, int]:
    height, width, _ = frame.shape
    if hasattr(iris, "__dict__"):
        indices = list(vars(iris).values())
    elif isinstance(iris, (list, tuple, np.ndarray)):
        indices = list(iris)
    elif isinstance(iris, int):
        indices = [iris]
    else:
        raise TypeError("iris must be a SimpleNamespace, list/tuple/ndarray of ints, or int")
    # Safety: filter indices within face bounds
    max_idx = face.shape[0] - 1
    indices = [i for i in indices if 0 <= int(i) <= max_idx]
    if not indices:
        return None
    xs = face[indices, 0] * width
    ys = face[indices, 1] * height
    iris_x = int(np.mean(xs))
    iris_y = int(np.mean(ys))
    return (iris_x, iris_y)

def get_points(frame: np.ndarray, face: np.ndarray, indices: int | list[int]):
    if isinstance(indices, int):
        indices = [indices]
        single = True
    else:
        single = False
    height, width, _ = frame.shape
    pts = [(int(face[i, 0] * width), int(face[i, 1] * height)) for i in indices]
    return pts[0] if single else pts

def draw_points(frame: np.ndarray, points: np.ndarray, color: tuple[int, int, int], radius: int):
    for x, y in points:
        cv2.circle(frame, (x, y), radius, color)

def draw_targets(frame, points, color=(0,0,255), radius=5):
    for x, y in points:
        cv2.circle(frame, (x, y), radius, color, -1)

# ##############################################################################
# Demonstration
# ##############################################################################

video = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)
print(video.isOpened())
full_width, full_height = get_screen_dimensions()
os.makedirs("logs", exist_ok=True)


# Main loop until 'q' is pressed.
while True:
    # Get a capture of the frame from the video.
    frame = get_frame_cap(video)
    if frame is None: continue
    frame = cv2.flip(frame, 1)
    blank = np.ones_like(frame, dtype=np.uint8) * 0
    frame_h, frame_w, _ = frame.shape

    # Detect the face in the frame with the FaceMesh object.
    face = detect_face(frame, mesh)
    if face is None: continue

    # Extract the eye and nose landmarks.
    eye_marks =  get_points(frame, face, Eye.indices())
    nose_marks = get_points(frame, face, Nose.indices())
    upper_lip = get_points(frame, face, Mouth.INNER.UPPER)
    lower_lip = get_points(frame, face, Mouth.INNER.LOWER)

    # Compute the iris positions.
    iris_left = detect_iris(frame, face, Eye.Left.Iris)
    iris_right = detect_iris(frame, face, Eye.Right.Iris)

    # Draw the face landmarks on the frame.
    draw_points(blank, eye_marks, State.GRABBED.color, 2)
    draw_points(blank, nose_marks, State.GRABBED.color, 2)
    draw_points(blank, upper_lip, State.GRABBED.color, 2)
    draw_points(blank, lower_lip, State.PULLING.color, 2)

    if iris_left is not None:
        draw_points(blank, [iris_left], State.GRABBED.color, 2)
    if iris_right is not None:
        draw_points(blank, [iris_right], State.GRABBED.color, 2)

    # Show the preview, with a copy of the frame in fullscreen.
    cv2.namedWindow("Preview", cv2.WINDOW_NORMAL)
    cv2.setWindowProperty("Preview", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    cv2.imshow("Preview", blank)

    # Press space to record a row or q to exit.
    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):
        continue
        # current_label = f"{CONFIG}_{HEADERS[i]}"
        # deltas.log(current_label, f"{CONFIG}_{TARGET}") # Important: edit this.
        # i = (i + 1) % len(HEADERS)
    elif key == ord('q'):
        break

# ### Clean up and exit ###
video.release()
cv2.destroyAllWindows()
