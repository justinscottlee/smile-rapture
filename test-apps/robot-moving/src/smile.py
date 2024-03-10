import zmq
import time

experiment_start_time = time.time()
debug = True

def __init(user_name: str):
    global context, socket, debug
    debug = False
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://smile-app-svc.{user_name}:5555")

"""Log a string message or other arbitrary (key, value) data to the SMILE web portal."""
def log(message: str, level="INFO", **data):
    if debug:
        return
    request = {
        "type": "LOG_STRING",
        "timestamp": time.time() - experiment_start_time,
        "level": level,
        "message": message
    }
    request.update(data)
    socket.send_json(request)
    response = socket.recv_json()
    return response["status"]

"""Retrieve the experiment ID."""
def get_experiment_id():
    if debug:
        return
    request = {
        "type": "GET_EXPERIMENT_ID",
    }
    socket.send_json(request)
    response = socket.recv_json()
    return response["experiment_id"]

def robot_moveforward(move_speed, move_time):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "FORWARD",
        "move_speed": move_speed,
        "move_time": move_time
    }
    socket.send_json(request)
    response = socket.recv_json()
    return response["status"]

def robot_movebackward(move_speed, move_time):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "BACKWARD",
        "move_speed": move_speed,
        "move_time": move_time
    }
    socket.send_json(request)
    response = socket.recv_json()
    return response["status"]

def robot_moveright(move_speed, move_time):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "RIGHT",
        "move_speed": move_speed,
        "move_time": move_time
    }
    socket.send_json(request)
    response = socket.recv_json()
    return response["status"]

def robot_moveleft(move_speed, move_time):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "LEFT",
        "move_speed": move_speed,
        "move_time": move_time
    }
    socket.send_json(request)
    response = socket.recv_json()
    return response["status"]