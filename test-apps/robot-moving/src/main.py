import smile
import cv2
import numpy as np
import subprocess
import select

print("program start")
socket = smile.robot_startvideostream("robo1", "5560")
print("got videostream socket")

ffmpeg_command = "ffmpeg -i - -pix_fmt bgr24 -f rawvideo -"
ffmpeg = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

while True:
    reads, writes, errors = select.select([ffmpeg.stdout, socket], [ffmpeg.stdin], [], 0.05)

    if ffmpeg.stdout in reads:
        raw_frame = ffmpeg.stdout.read(640*480*3)
        if raw_frame:
            image = np.frombuffer(raw_frame, np.uint8).reshape((480, 640, 3))
            print("got frame")
            print(cv2.mean(image))
    
    if socket in reads:
        data = socket.recv()
        ffmpeg.stdin.write(data)