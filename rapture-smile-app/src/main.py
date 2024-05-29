EXPERIMENT_UUID = "72334461b203499386f832eed9a9f64d"

import zmq
import requests
import time

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")
experiment_start_time = time.time()

def api_upload(json_data: dict):
    requests.post(f"http://130.191.162.166:5001/api/upload/{EXPERIMENT_UUID}", json=json_data)


request = {
        "type": "LOG_STRING",
        "timestamp": time.time() - experiment_start_time,
        "level": "INFO",
        "message": "RAPTURE Smile App initialized."
    }
api_upload(request)

while True:
    message = socket.recv_json()
    match message["type"]:
        case "LOG_STRING":
             message.update({"timestamp": time.time() - experiment_start_time})
             api_upload(message)
             socket.send_json({})
        case "GET_EXPERIMENT_ID":
            socket.send_json({"experiment_id": f"{EXPERIMENT_UUID}"})