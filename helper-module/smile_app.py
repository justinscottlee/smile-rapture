EXPERIMENT_ID = 1535

import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

while True:
    message = socket.recv_json()
    match message["type"]:
        case "LOG_STRING":
             print(message)
             socket.send_json({})
        case "GET_EXPERIMENT_ID":
            socket.send_json({"experiment_id": f"{EXPERIMENT_ID}"})