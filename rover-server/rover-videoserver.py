import cv2
import pickle
import socket
import sys

capture = cv2.VideoCapture(f"udp://0.0.0.0:5560")

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket.bind(("0.0.0.0", int(sys.argv[1])))
socket.listen(1)
client_socket, client_address = socket.accept()

while True:
    ret, frame = capture.read()
    if ret:
        data = pickle.dumps(frame)
        client_socket.sendall(data)