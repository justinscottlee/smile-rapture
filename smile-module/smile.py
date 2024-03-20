import zmq
import time

experiment_start_time = time.time()
debug = True
robot_sockets = {}

"""The RAPTURE web portal will automatically call this function to initialize the SMILE module with your username and robot names."""
def __init(user_name: str, robot_names: list[str]):
    global context, socket, debug, robot_sockets
    debug = False
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f"tcp://rapture-smile-app-svc.{user_name}:5555")
    for robot_name in robot_names:
        robot_socket = context.socket(zmq.REQ)
        robot_socket.connect(f"tcp://{robot_name}-rover-smile-app-svc.{user_name}:5555")
        robot_sockets[robot_name] = robot_socket


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


def robot_moveforward(robot_name: str, move_speed: int, move_time: float):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "FORWARD",
        "move_speed": move_speed,
        "move_time": move_time
    }
    robot_sockets[robot_name].send_json(request)
    response = robot_sockets[robot_name].recv_json()
    return response["status"]


def robot_movebackward(robot_name: str, move_speed: int, move_time: float):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "BACKWARD",
        "move_speed": move_speed,
        "move_time": move_time
    }
    robot_sockets[robot_name].send_json(request)
    response = robot_sockets[robot_name].recv_json()
    return response["status"]


def robot_moveright(robot_name: str, move_speed: int, move_time: float):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "RIGHT",
        "move_speed": move_speed,
        "move_time": move_time
    }
    robot_sockets[robot_name].send_json(request)
    response = robot_sockets[robot_name].recv_json()
    return response["status"]


def robot_moveleft(robot_name: str, move_speed: int, move_time: float):
    if debug:
        return
    request = {
        "type": "MOVE",
        "direction": "LEFT",
        "move_speed": move_speed,
        "move_time": move_time
    }
    robot_sockets[robot_name].send_json(request)
    response = robot_sockets[robot_name].recv_json()
    return response["status"]


def robot_turnright(robot_name: str, turn_speed: int, turn_time: float):
    if debug:
        return
    request = {
        "type": "TURN",
        "direction": "RIGHT",
        "turn_speed": turn_speed,
        "turn_time": turn_time
    }
    robot_sockets[robot_name].send_json(request)
    response = robot_sockets[robot_name].recv_json()
    return response["status"]


def robot_turnleft(robot_name: str, turn_speed: int, turn_time: float):
    if debug:
        return
    request = {
        "type": "TURN",
        "direction": "LEFT",
        "turn_speed": turn_speed,
        "turn_time": turn_time
    }
    robot_sockets[robot_name].send_json(request)
    response = robot_sockets[robot_name].recv_json()
    return response["status"]