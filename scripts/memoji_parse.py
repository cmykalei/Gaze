import cv2
import os
from rembg import remove
from PIL import Image
import subprocess

# === Step 1: Extract frames from video ===
video_path = "memoji.mp4"
frames_dir = "frames"
os.makedirs(frames_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
frame_num = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_path = os.path.join(frames_dir, f"frame_{frame_num:04d}.png")
    cv2.imwrite(frame_path, frame)
    frame_num += 1

cap.release()

# === Step 2: Remove background from each frame ===
cleaned_dir = "cleaned"
os.makedirs(cleaned_dir, exist_ok=True)

for filename in sorted(os.listdir(frames_dir)):
    if filename.endswith(".png"):
        input_path = os.path.join(frames_dir, filename)
        output_path = os.path.join(cleaned_dir, filename)

        with Image.open(input_path) as img:
            output = remove(img)
            output.save(output_path)


# === Step 3: Reassemble into transparent .webm ===
output_video = "memoji_clean.webm"

ffmpeg_cmd = [
    "ffmpeg",
    "-framerate", "30",
    "-i", os.path.join(cleaned_dir, "frame_%04d.png"),
    "-c:v", "libvpx",
    "-pix_fmt", "yuva420p",
    "-y", output_video
]

subprocess.run(ffmpeg_cmd)
