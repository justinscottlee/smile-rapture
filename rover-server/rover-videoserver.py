import subprocess
import zmq
import sys

context = zmq.Context()
sock = context.socket(zmq.PUSH)
sock.bind(f"tcp://0.0.0.0:{sys.argv[1]}")

ffmpeg_command = f"ffmpeg -f v4l2 -s 640x480 -i /dev/video0 -preset ultrafast -tune zerolatency -b 150k -maxrate 150k -bufsize 150k -codec h264 -framerate 15 -g 30 -bf 1 -f mpegts pipe:1"
proc = subprocess.Popen(ffmpeg_command.split(), stdout=subprocess.PIPE, stderr=sys.stderr)

while True:
    data = proc.stdout.read(1024)
    sock.send(data)