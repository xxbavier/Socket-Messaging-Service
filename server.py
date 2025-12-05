import socket
import multiprocessing as mp
import selectors
import types
import threading

from json import JSONEncoder, JSONDecoder

sel = selectors.DefaultSelector()

class Server():
    def __enter__(self):
        return self

    def __init__(self, host, port=0):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.processes = []
        self.monitor_thread = None

    def start(self):
        print(f"Starting server on {self.host}:{self.port}")
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        self.socket.setblocking(False)
        print("Server started and listening for connections.")

        sel.register(self.socket, selectors.EVENT_READ, data= None)

        try:
            self.monitor_thread = threading.Thread(target=self.monitor_clients)
            self.monitor_thread.start()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")

    def monitor_clients(self):
        try:
            while True:
                events = sel.select(timeout=None)
                for key, mask in events:
                    if key.data is None:
                        # New client
                        self.accept_client(key.fileobj)
                    else:
                        # Existing client
                        self.service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            sel.close()
        
    def accept_client(self, sock):
        conn, addr = sock.accept()
        conn.setblocking(False)
        print(f"Connected by {addr}")

        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        sel.register(conn, events, data=data)
            
    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                print(f"Received {recv_data!r} from {data.addr}")
                data.outb += recv_data
            else:
                self.unregister_client(sock)
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                decoded = data.outb.decode("utf-8")
                decoded = JSONDecoder().decode(decoded)

                if decoded[0] == "connect":
                    user = decoded[1]
                    self.clients[user] = sock

                elif decoded[0] == "disconnect":
                    user = decoded[1]
                    sock = self.clients.pop(user, None)

                    if sock:
                        self.unregister_client(sock)

                elif decoded[0] == "send":
                    target = decoded[1]
                    user = None
                    target_sock = self.clients.get(target)

                    for key, val in self.clients.items():
                        if val == sock:
                            user = key
                            break

                    if target_sock:
                        message = ["incoming message", user, decoded[2]]
                        message = JSONEncoder().encode(message)

                        sock.sendall(message.encode("utf-8"))

                #print(f"Echoing {data.outb!r} to {data.addr}")
                #sent = sock.send(data.outb)  # Should be ready to write
                #data.outb = data.outb[sent:]

    def unregister_client(self, sock):
        sel.unregister(sock)
        sock.close()
        print(f"Closing connection to {sock}.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Shutting down server.")
        sel.close()
        self.socket.close()
        print("Server shut down.")

        if exc_type:
            print(f"An exception of type {exc_type} occurred.")
        
        return False