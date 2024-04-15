import smile
import cv2
import numpy as np

print("program start")
socket = smile.robot_startvideostream("robo1", "5560")
print("got videostream socket")

while True:
    frame = socket.recv()
    print("got frame")
    array = np.frombuffer(frame, dtype=np.uint8)
    img = cv2.imdecode(array, 1)
    average_color = np.mean(img, axis=0)
    print(average_color)