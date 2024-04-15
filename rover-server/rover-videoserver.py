import cv2
import pickle
import zmq
import sys

capture = cv2.VideoCapture(f"udp://0.0.0.0:5560")
print("created videocapture")

context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.bind(f"tcp://0.0.0.0:{sys.argv[1]}")

while True:
    ret, frame = capture.read()
    if ret:
        print("got frame")
        sock.send_pyobj(frame)
        print("sent frame")
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break