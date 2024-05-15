import cv2
import os
import numpy as np
import zmq

from demosaic import demosaic
from dataclasses import dataclass

# cwd + images/
IMAGES_DIR = 'images/'

context = zmq.Context()


@dataclass
class Agent:
    addr: str = ""
    socket: zmq.SyncSocket = None


agents = [Agent(addr="tcp://agent1-svc.admin:5555"), Agent(addr="tcp://agent2-svc.admin:5555")]

def create_sockets(agents):
    """
    Create a ZMQ socket for each agent.
    """
    for agent in agents:
        agent.socket = context.socket(zmq.PAIR)
        agent.socket.connect(agent.addr)
        print("Connected to: ", agent.addr, agent.socket)


def import_images(dir_path):
    """
    Read a set of images from the filesystem (4-channel RGBA).
    """
    images = []

    for filename in os.listdir(dir_path):
        image = cv2.imread(os.path.join(dir_path, filename), cv2.IMREAD_GRAYSCALE)

        if not image is None:
            print("Imported: ", filename, " Shape: ", image.shape)
            images.append(image)

    return images


def distribute_images(images, agents):
    """
    Split a set of images into random subsets and send them to agents to be demosaicked.
    """
    agent_count = len(agents)

    agent_images = []
    for i in range(agent_count):
        agent_images.append([])
    
    for i, image in enumerate(images):
        print(f"Assigning image {i} to agent {i % agent_count}")
        agent_images[i % agent_count].append(image)

    # Send each agent their subset of images
    for i, image_set in enumerate(agent_images):
        print(f"Sending image set to agent {i}")
        agents[i].socket.send_pyobj(image_set)


def main():
    images = import_images(IMAGES_DIR)
    create_sockets(agents)

    
    distribute_images(images, agents)

    partially_demosaicked_images = []

    for agent in agents:
        partially_demosaicked_images = partially_demosaicked_images + agent.socket.recv_pyobj()

    print(f"Received {len(partially_demosaicked_images)} partially demosaicked images from agents.")
    demosaic(partially_demosaicked_images)
    print(f"Ending with {len(partially_demosaicked_images)} partially demosaicked images.")
    
    # program done now. Save image to disk or something?
    for i, image in enumerate(partially_demosaicked_images):
        cv2.imwrite(f"output_{i}.png", image)

if __name__ == '__main__':
    main()