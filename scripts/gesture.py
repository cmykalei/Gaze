import cv2
import mediapipe as mp
import numpy as np
import math
from enum import Enum
from typing import Dict
import gaze

# Custom class imports, see config.py
from config import Hand
from config import Display
from config import State

X = 0  # Horizontal axis.
Y = 1  # Vertical axis.
Z = 2  # Depth axis.

# Blocks class to manage blocks and their positions.
class Blocks:
    class Block:
        def __init__(self, pos: tuple[int, int], size: int = 50, id: str = "BLOCK") -> None:
            self.pos = pos
            self.size = size
            self.state = State.IDLE
            self.x1 = self.pos[0] - self.size // 2
            self.y1 = self.pos[1] - self.size // 2
            self.x2 = self.pos[0] + self.size // 2
            self.y2 = self.pos[1] + self.size // 2
            self.id = id

        def _is_hovered(self, finger_pos: tuple[int, int]) -> bool:
            fx, fy = finger_pos[:2]
            return (self.x1 <= fx <= self.x2) and (self.y1 <= fy <= self.y2)

        def _drag(self, finger_pos: tuple[int, int]):
            fx, fy = finger_pos[:2]
            self.pos = (fx, fy)
            half = self.size // 2
            self.x1 = fx - half
            self.y1 = fy - half
            self.x2 = fx + half
            self.y2 = fy + half

        def _pull(self, finger_pos: tuple[int, int]):
            fy = finger_pos[1]
            cy = (self.y1 + self.y2) // 2
            dy = fy - cy

            scale = 0.1
            delta = int(abs(dy) * scale)

            new_width = (self.x2 - self.x1) + (delta * 2 if dy > 0 else -delta * 2)
            new_height = (self.y2 - self.y1) + (delta * 2 if dy > 0 else -delta * 2)

            if new_width >= 50 and new_height >= 50 and new_width < 800 and new_height < 800:
                if dy > 0:
                    self.x1 -= delta
                    self.x2 += delta
                    self.y1 -= delta
                    self.y2 += delta
                else:
                    self.x1 += delta
                    self.x2 -= delta
                    self.y1 += delta
                    self.y2 -= delta

        def _resize(self):
            cx = (self.x1 + self.x2) // 2
            cy = (self.y1 + self.y2) // 2
            self.pos = (cx, cy)
            self.size = (self.x2 - self.x1)

        def draw(self, frame: np.ndarray, gesture: State, finger_pos=None):
            if finger_pos:
                if gesture != State.IDLE and gesture != State.DROPPED and gesture != State.REACHING:
                    if self.state == State.PULLING and gesture == State.PULLING:
                        self._pull(finger_pos)
                        self._resize()
                    elif self.state == State.DRAGGING and gesture == State.DRAGGING:
                        self._drag(finger_pos)
                    else:
                        if self._is_hovered(finger_pos):
                            if self.state == State.IDLE and gesture == State.SELECTED:
                                self.state = State.SELECTED
                            elif self.state == State.SELECTED:
                                if gesture == State.GRABBED or gesture == State.PULLING:
                                    self.state = gesture
                            elif self.state == State.GRABBED and gesture == State.DRAGGING:
                                self.state = State.DRAGGING
                        else:
                            if self.state == State.DRAGGING and gesture == State.DRAGGING and gesture != State.PULLING:
                                self.state = State.DROPPED
                else:
                    self.state = State.IDLE
            else:
                self.state = State.IDLE
            cv2.rectangle(
                frame,
                (self.x1, self.y1),
                (self.x2, self.y2),
                self.state.color, 2
            )

            for i in range(4):
                cv2.circle(
                    frame,
                    (self.pos[0] + (i * 20), self.pos[1] + (i * 20)),
                    10, self.state.color, -1
                )
            
            cv2.putText(
                frame,
                f"{self.state.name}",
                (self.x1, self.y1 - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                self.state.color, 2
            )

        def clamp(self, finger_pos) -> tuple[int, int]:
            cx, cy = self.pos
            fx, fy = finger_pos[:2]
            half = self.size // 2
            clamped_x = max(cx - half, min(fx, cx + half))
            clamped_y = max(cy - half, min(fy, cy + half))
            return (clamped_x, clamped_y)

    def __init__(self):
        self.blocks: Dict[str, Block] = {}
        self.boundary: Blocks.Block = None

    def setup(self, screen_width: int, screen_height: int):
        center = (screen_width // 2, screen_height // 2)
        size = max(screen_width, screen_height)
        self.boundary = Blocks.Block(center, size)

    def add_block(self, block_id: str, center, size=40):
        cx, cy = self.boundary.clamp(center)
        self.blocks[block_id] = Blocks.Block((cx, cy), size, block_id)

    def draw(self, frame: np.ndarray, state: State, finger_pos: tuple[int, int]=None):
        for block_id, block in self.blocks.items():
            frame = block.draw(frame, state, finger_pos)

# Gesture class to detect and show a current gesture.
class Gesture:

    def __init__(self):
        # Initialise MediaPipe resources.
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_mesh = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # CHANGED: allow two hands
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5)

        # Positions/state per hand label.
        self.hands = {
            "Left": {
                "pos": {}, "seq": State.IDLE,
                "moved_x": 0, "moved_y": 0, "moved_z": 0, "timer": 0, "timeout": False
            },
            "Right": {
                "pos": {}, "seq": State.IDLE,
                "moved_x": 0, "moved_y": 0, "moved_z": 0, "timer": 0, "timeout": False
            }
        }

        # Keep a short-hand of the most recent overall landmarks object
        self.landmarks = None

        # Indices helper (shared)
        self.hand = Hand()
        self.indices = self.hand.indices()

    # Function get_area computes the area of a triangle from three point indices for a given hand pos.
    def _area(self, a, b, c, pos) -> float:
        ax, ay = pos[a][X], pos[a][Y]
        bx, by = pos[b][X], pos[b][Y]
        cx, cy = pos[c][X], pos[c][Y]
        t1 = ax * (by - cy)
        t2 = bx * (cy - ay)
        t3 = cx * (ay - by)
        return abs((t1 + t2 + t3) / 2)

    # Function get_distance computes the difference between two point indices for a given hand pos.
    def _distance(self, a, b, pos) -> float:
        ax, ay = pos[a][X], pos[a][Y]
        bx, by = pos[b][X], pos[b][Y]
        dx = (ax - bx) ** 2
        dy = (ay - by) ** 2
        return (dx + dy) ** 0.5

    # Function is_straight checks if a finger is flexed on all axes for a given hand pos.
    def _is_straight(self, finger, pos):
        a = np.array(pos[finger.BASE])
        b = np.array(pos[finger.DIP])
        c = np.array(pos[finger.TIP])
        ab = b - a
        bc = c - b
        ab_norm = ab / np.linalg.norm(ab)
        bc_norm = bc / np.linalg.norm(bc)
        return np.dot(ab_norm, bc_norm) > 0.98

    # Function is_open checks if any fingers are straight for a given hand pos.
    def _is_open(self, *fingers, pos):
        return any(self._is_straight(f, pos) for f in fingers)

    # Function is_pinched checks if a finger is on the thumb for a given hand pos.
    def _is_pinched(self, finger, pos):
        if not (self.hand.Middle.BASE in pos and self.hand.WRIST in pos and
                self.hand.Thumb.TIP in pos and finger.TIP in pos):
            return False
        palm_height = self._distance(self.hand.Middle.BASE, self.hand.WRIST, pos)
        pinch_height = self._distance(self.hand.Thumb.TIP, finger.TIP, pos)
        return pinch_height < palm_height * 0.3

    # Function is_lifted checks if the current depth is less than the previous (per hand label).
    def _is_lifted(self, finger, label: str, t=0.01):
        pos = self.hands[label]["pos"]
        if finger.TIP not in pos:
            return False
        curr_z = pos[finger.TIP][Z]
        prev_z = self.hands[label]["moved_z"]
        return (curr_z - prev_z) > t

    # Function is_moved checks if the current position is different (per hand label).
    def _is_moved(self, finger, label: str, t=1):
        pos = self.hands[label]["pos"]
        if finger.TIP not in pos:
            return False
        curr_x = pos[finger.TIP][X]
        curr_y = pos[finger.TIP][Y]
        prev_x = self.hands[label]["moved_x"]
        prev_y = self.hands[label]["moved_y"]
        dx = curr_x - prev_x
        dy = curr_y - prev_y
        distance = ((dx ** 2) + (dy ** 2)) ** 0.5
        return distance > t

    # Function _detect runs the state machine for a given hand label.
    def _detect(self, label: str) -> State:
        pos = self.hands[label]["pos"]
        if not pos:
            return self.hands[label]["seq"]

        seq = self.hands[label]["seq"]
        timer = self.hands[label]["timer"]
        timeout = self.hands[label]["timeout"]
        moved_x = self.hands[label]["moved_x"]
        moved_y = self.hands[label]["moved_y"]
        moved_z = self.hands[label]["moved_z"]

        # Read conditions using per-hand pos and motion
        index_selected = self._is_pinched(self.hand.Index, pos=pos)
        middle_selected = self._is_pinched(self.hand.Middle, pos=pos)
        hand_flexed = self._is_open(self.hand.Index, pos=pos)
        hand_lifted = self._is_lifted(self.hand.Index, label)
        hand_moved = self._is_moved(self.hand.Index, label)

        if seq == State.IDLE:
            if timeout and hand_flexed:
                timeout = False
                timer = 0
            if not timeout and hand_flexed and not index_selected:
                seq = State.REACHING
        elif seq == State.REACHING:
            timer += 1
            if timer > 5 and index_selected:
                moved_z = pos[self.hand.Index.TIP][Z]
                timer = 0
                seq = State.SELECTED
            if not index_selected and timer > 10:
                timeout = True
                seq = State.IDLE
        elif seq == State.SELECTED:
            timer += 1
            if timer > 5:
                if index_selected and not middle_selected:
                    if hand_lifted:
                        timer = 0
                        seq = State.PULLING
                elif index_selected and middle_selected:
                    if hand_lifted:
                        timer = 0
                        seq = State.GRABBED
                else:
                    seq = State.IDLE
                    timer = 0
        elif seq == State.GRABBED:
            moved_x = pos[self.hand.Index.TIP][X]
            moved_y = pos[self.hand.Index.TIP][Y]
            timer += 1
            if timer > 5 and hand_moved:
                seq = State.DRAGGING
                timer = 0
        elif seq == State.PULLING:
            timer += 1
            if timer > 5 and not index_selected:
                timer = 0
                seq = State.DROPPED
        elif seq == State.DRAGGING:
            timer += 1
            if timer > 5 and not index_selected and hand_flexed:
                timer = 0
                seq = State.DROPPED
        elif seq == State.DROPPED:
            timer += 1
            if timer > 5:
                seq = State.IDLE

        # Replace with updated values before returning
        self.hands[label]["seq"] = seq
        self.hands[label]["timer"] = timer
        self.hands[label]["timeout"] = timeout
        self.hands[label]["moved_x"] = moved_x
        self.hands[label]["moved_y"] = moved_y
        self.hands[label]["moved_z"] = moved_z
        return seq

    # Function detects the gesture and updates the current state and sequence.
    def detect(self, frame: np.ndarray):
        # Clear per-hand positions each frame.
        self.hands["Left"]["pos"].clear()
        self.hands["Right"]["pos"].clear()
        h, w = frame.shape[:2]

        # Extract and process the landmarks from the frame.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.landmarks = self.mp_mesh.process(rgb)

        # Detect hands and store per-hand positions using handedness labels.
        if self.landmarks and self.landmarks.multi_hand_landmarks:
            for lm_set, handed in zip(self.landmarks.multi_hand_landmarks, self.landmarks.multi_handedness):
                label = handed.classification[0].label  # "Left" or "Right"
                pos = self.hands[label]["pos"]
                for i in self.indices:
                    x = int(lm_set.landmark[i].x * w)
                    y = int(lm_set.landmark[i].y * h)
                    z = lm_set.landmark[i].z
                    pos[i] = (x, y, z)

        # Run per-hand state machine.
        left_state = self._detect("Left")
        right_state = self._detect("Right")
        return {"Left": left_state, "Right": right_state}

    # Function draws the gesture on the frame.
    def draw(self, frame: np.ndarray, current: Dict[str, State]):
        # Draw both hands if present.
        if not self.landmarks or not self.landmarks.multi_hand_landmarks:
            return
        y0 = 30
        for label in ("Left", "Right"):
            cv2.putText(
                frame,
                f"{label}: {current[label].name}",
                (10, y0),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                State.REACHING.color, 2)
            y0 += 30

        h, w = frame.shape[:2]
        for lm_set in self.landmarks.multi_hand_landmarks:
            for lm in lm_set.landmark:
                x = int(lm.x * w)
                y = int(lm.y * h)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)  # Green circles for all points

        # Draw circles for thumbs and index tips for both hands
        for label in ("Left", "Right"):
            if self.hands[label]["seq"] != State.IDLE:
                pos = self.hands[label]["pos"]
                # if self.hand.Thumb.TIP in pos and self.hand.Index.TIP in pos:
                #    for x, y in [pos[self.hand.Thumb.TIP][:2], pos[self.hand.Index.TIP][:2]]:
                #        cv2.circle(frame, (x, y), 20, current[label].color, -1)


# Get screen size once.
import tkinter as tk
root = tk.Tk(); root.withdraw()
screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
root.destroy()
win = "Hands"
cv2.namedWindow(win, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
video = cv2.VideoCapture(0)
gesture = Gesture()
blocks = Blocks()

while True:
    success, frame = video.read()
    if success:
        h, w = frame.shape[:2]
        blocks.setup(w, h)
        blocks.add_block("block_0", (w // 2, h // 2), size=100)
        break

# Loop until 'q' is pressed for exit.
while True:
    # Get the frame and check if read was ok.
    ok, frame = video.read()
    if not ok:
        continue

    frame = cv2.flip(frame, 1)
    state = gesture.detect(frame)  # dict: {"Left": State, "Right": State}
    gesture.draw(frame, state)

    # Choose a controlling hand's index finger position (prefer Right, else Left).
    right_index_pos = gesture.hands["Right"]["pos"].get(gesture.hand.Index.TIP)
    left_index_pos = gesture.hands["Left"]["pos"].get(gesture.hand.Index.TIP)
    index_pos = right_index_pos or left_index_pos
    control_state = state["Right"] if index_pos is right_index_pos else state["Left"]

    # Draw blocks (no frame return, just mutates frame)
    blocks.draw(frame, control_state, index_pos)

    cv2.imshow("Hands", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()

