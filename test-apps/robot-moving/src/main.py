import smile
import cv2
import numpy as np
print("program start")
socket, addr = smile.robot_startvideostream("robo1", "5560")
print("got videostream socket")

cap = cv2.VideoCapture(addr, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("error opening video stream")

while True:
    ret, frame = cap.read()
    if ret:
        print(frame.shape)
        print(cv2.mean(frame))