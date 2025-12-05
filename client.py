import socket
from tkinter import Tk, ttk
import selectors
import types
import threading
import errno

from json import JSONEncoder, JSONDecoder

sel = selectors.DefaultSelector()

class Client():
    def __init__(self, host, port, username):
        self.username = username
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.connection_thread = None

    def create_gui(self):
        self.root = Tk()
        self.root.title(f"{self.username} Window")
        self.root.geometry("300x200")
        frame = ttk.Frame(self.root)

        self.root.mainloop()

    def connect(self):
        print(f"Connecting to {self.host}:{self.port}")
        error_code = self.socket.connect_ex((self.host, self.port))
        
        if error_code == 0:
            self.on_successful_connection()
        elif error_code in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
            print("Connection in progress. Waiting for completion...")
            data = types.SimpleNamespace(setup= True, is_connecting=True, outb=b"")
            sel.register(self.socket, selectors.EVENT_WRITE, data=data)
            
            try:
                self.connection_thread = threading.Thread(target=self.monitor_connection)
                self.connection_thread.start()
            except KeyboardInterrupt:
                print("Caught keyboard interrupt, exiting")
        else:
            print(f"Connection failed with error code: {error_code}")
            self.disconnect()
            return        

    def on_successful_connection(self):
        print("Connected to server!")
        connection_message = ["connect", self.username]
        connection_message = JSONEncoder().encode(connection_message)

        self.socket.sendall(connection_message.encode("utf-8"))

        try:
            self.connection_thread = threading.Thread(target=self.monitor_connection)
            self.connection_thread.start()
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")

    def monitor_connection(self):
        try:
            while True:
                events = sel.select(timeout=None)
                for key, mask in events:
                    self.service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            print("Closing selector...")
            sel.close()
    
    def disconnect(self):
        print("Disconnecting from server.")
        self.socket.close()
        print("Disconnected.")

    def send_message(self, recipient, message):
        events = selectors.EVENT_READ | selectors.EVENT_WRITE

        message = ["send", recipient, message]
        message = JSONEncoder().encode(message)

        data = types.SimpleNamespace(
            setup=False,
            connid=self.username,
            destination= recipient,
            message = [message],
            outb=b""
        )
        sel.register(self.socket, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        
        if data.setup:
            if data.is_connecting:
                sel.unregister(sock)
                err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                
                if err == 0:
                    data.is_connecting = False
                    self.on_successful_connection()
                    
                    #sel.register(sock, selectors.EVENT_READ | selectors.EVENT_WRITE, data=data)
                else:
                    print(f"Connection failed during completion: Error {err} ({errno.errorcode.get(err)})")
                    self.disconnect()
                
                return
        else:
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(1024)  # Should be ready to read
                if recv_data:
                    data = recv_data.decode("utf-8")
                    data = JSONDecoder().decode(data)

                    if data[0] == "incoming message":
                        sender = data[1]
                        message = data[2]

                        print(f"Message from {sender}: {message}")

                if not recv_data:
                    print(f"Closing connection {data.connid}")
                    sel.unregister(sock)
                    sock.close()
            if mask & selectors.EVENT_WRITE:
                if not data.outb and data.message:
                    data.outb = bytes(data.message.pop(0).encode("utf-8"))
                if data.outb:
                    #print(f"Sending {data.outb!r} to connection {data.connid}")
                    sent = sock.send(data.outb)  # Should be ready to write
                    data.outb = data.outb[sent:]