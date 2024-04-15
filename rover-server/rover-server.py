import zmq
import time
import makeblock
import subprocess

gst_pipelines = {}

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

bot = makeblock.MegaPi.connect()
motor_rightbow = bot.DCMotor(1,1)
motor_rightstern = bot.DCMotor(1,2)
motor_leftbow = bot.DCMotor(2,2)
motor_leftstern = bot.DCMotor(2,1)

def move_stop():
    motor_rightbow.run(0)
    motor_rightstern.run(0)
    motor_leftbow.run(0)
    motor_leftstern.run(0)

def move_forward(move_speed: int, move_time: float):
    motor_rightbow.run(move_speed)
    motor_rightstern.run(move_speed)
    motor_leftbow.run(-move_speed)
    motor_leftstern.run(-move_speed)
    time.sleep(move_time)
    move_stop()

def move_backward(move_speed: int, move_time: float):
    motor_rightbow.run(-move_speed)
    motor_rightstern.run(-move_speed)
    motor_leftbow.run(move_speed)
    motor_leftstern.run(move_speed)
    time.sleep(move_time)
    move_stop()

def move_left(move_speed: int, move_time: float):
    motor_rightbow.run(move_speed)
    motor_rightstern.run(-move_speed)
    motor_leftbow.run(move_speed)
    motor_leftstern.run(-move_speed)
    time.sleep(move_time)
    move_stop()

def move_right(move_speed: int, move_time: float):
    motor_rightbow.run(-move_speed)
    motor_rightstern.run(move_speed)
    motor_leftbow.run(-move_speed)
    motor_leftstern.run(move_speed)
    time.sleep(move_time)
    move_stop()

def turn_right(turn_speed: int, turn_time: float):
    motor_rightbow.run(-turn_speed)
    motor_rightstern.run(-turn_speed)
    motor_leftbow.run(-turn_speed)
    motor_leftstern.run(-turn_speed)
    time.sleep(turn_time)
    move_stop()

def turn_left(turn_speed: int, turn_time: float):
    motor_rightbow.run(turn_speed)
    motor_rightstern.run(turn_speed)
    motor_leftbow.run(turn_speed)
    motor_leftstern.run(turn_speed)
    time.sleep(turn_time)
    move_stop()

while True:
    message = socket.recv_json()
    match message["type"]:
        case "START_VIDEO_STREAM":
            ffmpeg_command = f"ffmpeg -f v4l2 -s 640x480 -i /dev/video0 -preset ultrafast -tune zerolatency -b 250k -codec h264 -framerate 15 -g 30 -bf 1 -f mpegts udp://127.0.0.1:5560"
            subprocess.Popen(ffmpeg_command.split())
            videoserver_command = f"python3 rover-videoserver.py 5560"
            subprocess.Popen(videoserver_command.split())
            socket.send_json({"status": "OK"})
        case "MOVE":
            move_speed: int = message["move_speed"]
            move_time: float = message["move_time"]
            match message["direction"]:
                case "FORWARD":
                    move_forward(move_speed, move_time)
                    socket.send_json({"status": "OK"})
                case "BACKWARD":
                    move_backward(move_speed, move_time)
                    socket.send_json({"status": "OK"})
                case "LEFT":
                    move_left(move_speed, move_time)
                    socket.send_json({"status": "OK"})
                case "RIGHT":
                    move_right(move_speed, move_time)
                    socket.send_json({"status": "OK"})
        case "TURN":
            turn_speed: int = message["turn_speed"]
            turn_time: float = message["turn_time"]
            match message["direction"]:
                case "LEFT":
                    turn_left(turn_speed, turn_time)
                    socket.send_json({"status": "OK"})
                case "RIGHT":
                    turn_right(turn_speed, turn_time)
                    socket.send_json({"status": "OK"})