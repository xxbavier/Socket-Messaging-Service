import socket

HOST = " "  # The server's hostname or IP address
PORT = 0  # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))

    print("Connected to server!")

    

    s.sendall(b"Hello, world")
    data = s.recv(1024)

print(f"Received {data!r}")