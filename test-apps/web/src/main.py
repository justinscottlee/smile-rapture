from flask import Flask, render_template, request
import socket
import random

HOST = "app0-svc.jlee1158"
PORT = [5006]

app = Flask(__name__)

messages = []

@app.route('/', methods=['GET', 'POST'])
def index():
	if request.method == 'POST':
		message = request.form['message']
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.connect((HOST, random.choice(PORT)))
			s.send(bytes(message.encode('utf8')))
			data = s.recv(1024)
			data = str(data)
			messages.append(f"{data}")
		return render_template('index.html', messages=messages)
	elif request.method == 'GET':
		return render_template('index.html', messages=messages)

port=5005
app.run(host="0.0.0.0", port=port)
