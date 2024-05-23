import zmq
import sys

from demosaic import demosaic

port = sys.argv[1]

context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.bind(f"tcp://*:{port}")


if __name__ == '__main__':
    while True:
        print("Waiting for images...")
        images = socket.recv_pyobj()
        print(f"Agent {port} received {len(images)} images. Demosaicking...")
        demosaic(images)
        print(f"Agent {port} has demosaicked down to {len(images)} images. Sending back...")
        socket.send_pyobj(images)
