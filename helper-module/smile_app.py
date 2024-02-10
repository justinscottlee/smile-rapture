EXPERIMENT_UUID = "ef24a69500bf4327908ab54faaabf39b"

import zmq
import requests

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

def api_upload(json_data: dict):
    requests.post(f"http://localhost:5001/api/upload/{EXPERIMENT_UUID}", json=json_data)

while True:
    message = socket.recv_json()
    match message["type"]:
        case "LOG_STRING":
             api_upload(message)
             socket.send_json({})
        case "GET_EXPERIMENT_ID":
            socket.send_json({"experiment_id": f"{EXPERIMENT_UUID}"})