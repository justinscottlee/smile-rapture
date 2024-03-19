ROBOT_NAME = "rpi4"

import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

robot_socket = context.socket(zmq.REQ)
robot_socket.connect(f"tcp://{ROBOT_NAME}:5555")

while True:
    request = socket.recv_json()
    robot_socket.send_json(request)
    response = robot_socket.recv_json()
    socket.send_json(response)