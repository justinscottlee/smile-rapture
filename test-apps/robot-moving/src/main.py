import smile
import cv2
import numpy as np

socket = smile.robot_startvideostream("robo1", "5560")

while True:
    frame = socket.recv()
    array = np.frombuffer(frame, dtype=np.uint8)
    img = cv2.imdecode(array, 1)
    average_color = np.mean(img, axis=0)
    print(average_color)