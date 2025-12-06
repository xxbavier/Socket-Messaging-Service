import socket
import multiprocessing as mp
import selectors
import types
import threading

from colorama import Fore, Style
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
        self.stop_event = threading.Event()

    def start(self):
        print(f"Starting server on {self.host}:{self.port}")
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen()
        self.socket.setblocking(False)
        print("Server started and listening for connections.")

        sel.register(self.socket, selectors.EVENT_READ, data= None)

        try:
            thread = threading.Thread(target=self.monitor_clients, args=(self.stop_event,))
            thread.start()

            while thread.is_alive():
                thread.join()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.__exit__(None, None, None)

    def monitor_clients(self, stop_event):
        while not stop_event.is_set():
            if sel.get_map() and len(sel.get_map()) == 0:
                continue

            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    # New client
                    self.accept_client(key.fileobj)
                else:
                    # Existing client
                    self.service_connection(key, mask)
        
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
                data.inb += recv_data

                try:
                    decoded = data.inb.decode("utf-8")
                    decoded = JSONDecoder().decode(decoded)
                    data.inb = b""

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

                        if target_sock and user:
                            message = ["incoming message", user, decoded[2]]
                            encoded_message = JSONEncoder().encode(message).encode("utf-8")

                            target_key = sel.get_key(target_sock)
                            target_data = target_key.data

                            target_data.outb += encoded_message
                except ValueError:
                    pass
                
                data.outb += recv_data
            else:
                self.unregister_client(sock)
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                sent = sock.send(data.outb)
                print(f"\nSent {Fore.CYAN}{sent}{Style.RESET_ALL} bytes to {Fore.MAGENTA}{data.addr}{Style.RESET_ALL}")
                data.outb = data.outb[sent:]

    def unregister_client(self, sock):
        sel.unregister(sock)
        sock.close()
        print(f"Closing connection to {sock}.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Shutting down server.")

        self.stop_event.set()

        for client in self.clients.values():
            self.unregister_client(client)

        sel.unregister(self.socket)
        sel.close()
        self.socket.close()
        print("Server shut down.")

        if exc_type:
            print(f"An exception of type {exc_type} occurred.")
        
        return False