import zmq
import time
import makeblock

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

def move_foward(move_speed, move_time):
    motor_rightbow.run(move_speed)
    motor_rightstern.run(move_speed)
    motor_leftbow.run(-move_speed)
    motor_leftstern.run(-move_speed)
    time.sleep(move_time)
    bot.move_stop()

def move_backward(move_speed, move_time):
    motor_rightbow.run(-move_speed)
    motor_rightstern.run(-move_speed)
    motor_leftbow.run(move_speed)
    motor_leftstern.run(move_speed)
    time.sleep(move_time)
    bot.move_stop()

def move_left(move_speed, move_time):
    motor_rightbow.run(move_speed)
    motor_rightstern.run(-move_speed)
    motor_leftbow.run(move_speed)
    motor_leftstern.run(-move_speed)
    time.sleep(move_time)
    bot.move_stop()

def move_right(move_speed, move_time):
    motor_rightbow.run(-move_speed)
    motor_rightstern.run(move_speed)
    motor_leftbow.run(-move_speed)
    motor_leftstern.run(move_speed)
    time.sleep(move_time)
    bot.move_stop()

def turn_right(turn_speed, turn_time):
    motor_rightbow.run(-turn_speed)
    motor_rightstern.run(-turn_speed)
    motor_leftbow.run(-turn_speed)
    motor_leftstern.run(-turn_speed)
    time.sleep(turn_time)
    bot.move_stop()

def turn_left(turn_speed, turn_time):
    motor_rightbow.run(turn_speed)
    motor_rightstern.run(turn_speed)
    motor_leftbow.run(turn_speed)
    motor_leftstern.run(turn_speed)
    time.sleep(turn_time)
    bot.move_stop()

while True:
    message = socket.recv_json()
    match message["type"]:
        case "MOVE":
            move_speed = message["move_speed"]
            move_time = message["move_time"]
            match message["direction"]:
                case "FORWARD":
                    print("Moving forward")
                    move_foward(move_speed, move_time)
                    socket.send_json({"status": "OK"})
                case "BACKWARD":
                    print("Moving backward")
                    move_backward(move_speed, move_time)
                    socket.send_json({"status": "OK"})
                case "LEFT":
                    print("Moving left")
                    move_left(move_speed, move_time)
                    socket.send_json({"status": "OK"})
                case "RIGHT":
                    print("Moving right")
                    move_right(move_speed, move_time)
                    socket.send_json({"status": "OK"})
        case "TURN":
            turn_speed = message["turn_speed"]
            turn_time = message["turn_time"]
            match message["direction"]:
                case "LEFT":
                    print("Turning left")
                    turn_left(turn_speed, turn_time)
                    socket.send_json({"status": "OK"})
                case "RIGHT":
                    print("Turning right")
                    turn_right(turn_speed, turn_time)
                    socket.send_json({"status": "OK"})