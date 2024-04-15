import smile
import cv2
import numpy as np
print("program start")
socket = smile.robot_startvideostream("robo1", "5560")
print("got videostream socket")

while True:
    frame = socket.recv_pyobj()
    print("got frame")
    print(frame.shape)
    print(cv2.mean(frame))