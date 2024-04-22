import smile
import cv2

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if ret:
        frame = cv2.resize(frame, (640, 480))
        print(cv2.mean(frame))