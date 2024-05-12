import os
import zmq

from demosaic import demosaic

context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.bind("tcp://*:5555")


if __name__ == '__main__':
    while True:
        print("Waiting for images...")
        images = socket.recv_pyobj()
        print("Received images, demosaicking...")
        demosaic(images)
        print("Demosaicking complete, sending stitched images...")
        socket.send_pyobj(images)
        print("Sent stitched images.")
