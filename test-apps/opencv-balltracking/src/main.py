import smile
import time

import cv2
import numpy as np

print("Starting video capture...", end=" ")
cap = smile.robot_startvideostream()
cap.set(cv2.CAP_PROP_FPS, 15)
print("Done.")

MIN_CNT_RADIUS = 10

greenLower = (0, 0, 200)
greenUpper = (100, 100, 255)

def get_frame():
    ret, frame = cap.read()
    if not ret:
        return None
    return frame

def thresh(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, greenLower, greenUpper)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    return mask

def find_biggest_circle(mask, raw_frame=None):
    # Find contours in the mask and initialize the current (x, y) center of the ball
    cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_radius = 0
    max_center = None
    max_circularity = 0
    circular_center = None
    circular_radius = 0

    for c in cnts:
        # Calculate area and perimeter of the contour
        area = cv2.contourArea(c)
        perimeter = cv2.arcLength(c, True)

        # Avoid division by zero
        if perimeter == 0:
            continue

        # Calculate circularity
        circularity = (4 * 3.14159 * area) / (perimeter * perimeter)

        ((x, y), radius) = cv2.minEnclosingCircle(c)
        if radius > max_radius:
            max_radius = radius
            max_center = (x, y)

        # Update the most circular contour
        if circularity > max_circularity:
            max_circularity = circularity
            circular_center = (int(x), int(y))
            circular_radius = int(radius)
        
    return max_center, max_radius, circular_center, circular_radius

def get_frame_width():
    time.sleep(1)
    first_frame = get_frame()

    print("Getting frame width...", end=" ")

    while first_frame is None:
        first_frame = get_frame()

    print("Done")
    return int(first_frame.shape[1])

frame_width = get_frame_width()
while True:
    raw_frame = get_frame()
    if raw_frame is None:
        continue

    mask = thresh(raw_frame)

    lr, target_size, _, _ = find_biggest_circle(mask, raw_frame)

    if lr is None:
        continue
    
    lr = lr[0] / frame_width

    if lr < 0.3:
        smile.robot_turnleft("robo1", 60, 0.035)
    elif lr > 0.7:
        smile.robot_turnright("robo1", 60, 0.035)
    else:
        smile.robot_moveforward("robo1", 40, 0.065)