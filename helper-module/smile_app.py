EXPERIMENT_ID = "8107013c8f744b308740d4c60cd83e2a"

import zmq
import requests

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

def api_upload(json_data: dict):
    requests.post(f"http://localhost:5001/api/upload/{EXPERIMENT_ID}", json=json_data)

while True:
    message = socket.recv_json()
    match message["type"]:
        case "LOG_STRING":
             api_upload(message)
             socket.send_json({})
        case "GET_EXPERIMENT_ID":
            socket.send_json({"experiment_id": f"{EXPERIMENT_ID}"})