import zmq
import time

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

experiment_start_time = time.time()

"""Log a string message or other arbitrary (key, value) data to the SMILE web portal."""
def log(message: str, level="INFO", **data):
    request = {
        "type": "LOG_STRING",
        "timestamp": time.time(),
        "level": level,
        "message": message
    }
    request.update(data)
    socket.send_json(request)
    socket.recv_string()

"""Retrieve the experiment ID."""
def get_experiment_id():
    request = {
        "type": "GET_EXPERIMENT_ID",
    }
    socket.send_json(request)
    response = socket.recv_json()
    return response["experiment_id"]