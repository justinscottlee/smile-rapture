import smile
import cv2
import numpy as np

smile.robot_startvideostream("robo1", "cont1-svc.admin", "5560")

capture = cv2.VideoCapture("tcp://0.0.0.0:5560")

while True:
    ret, frame = capture.read()

    if not ret:
        print("no frame")

    average_color_per_row = np.mean(frame, axis=0)
    average_color = np.mean(average_color_per_row, axis=0)
    average_color = np.uint8(average_color)[::-1]
    print("Average Color: ", average_color)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break