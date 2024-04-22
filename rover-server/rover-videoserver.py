import subprocess
import zmq
import sys
import cv2

context = zmq.Context()
sock = context.socket(zmq.PUSH)
sock.bind(f"tcp://0.0.0.0:{sys.argv[1]}")

ffmpeg_command = f"ffmpeg -f v4l2 -s 640x480 -i /dev/video0 -preset ultrafast -tune zerolatency -b 150k -maxrate 150k -bufsize 150k -codec h264 -framerate 15 -g 30 -bf 1 -f mpegts udp://127.0.0.1:5550"
subprocess.Popen(ffmpeg_command.split())

capture = cv2.VideoCapture("udp://0.0.0.0:5550", cv2.CAP_FFMPEG)

while True:
    ret, frame = capture.read()
    if ret:
        sock.send(frame.tobytes())