import socket
import select

HOST = "0.0.0.0"
PORT1 = 5006

s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s1.bind((HOST, PORT1))

s1.listen()

server_sockets = [s1]
read_list = [s1]
while True:
	readable, writable, errored = select.select(read_list, [], [])
	for s in readable:
		if s in server_sockets:
			client_socket, addr = s.accept()
			read_list.append(client_socket)
		else:
			data = s.recv(1024)
			data = str(data)
			response = f"Successfully received {data}"
			s.send(bytes(response.encode('utf8')))
			s.close()
			read_list.remove(s)
