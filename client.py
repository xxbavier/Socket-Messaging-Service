import socket
from tkinter import Tk, ttk
import selectors
import types
import threading
import errno

from colorama import Fore, Back, Style
from json import JSONEncoder, JSONDecoder

sel = selectors.DefaultSelector()

class Client():
    def __init__(self, host, port, username):
        self.username = username
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(False)
        self.connStopEvent = threading.Event()

        self.disconnecting_mutex = False

    '''def create_gui(self):
        self.root = Tk()
        self.root.title(f"{self.username} Window")
        self.root.geometry("300x200")
        frame = ttk.Frame(self.root)

        self.root.mainloop()'''

    def connect(self):
        print(f"Connecting to {self.host}:{self.port}")
        error_code = self.socket.connect_ex((self.host, self.port))
        
        if error_code == 0:
            self.on_successful_connection()
        elif error_code in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
            self.on_successful_connection(is_connecting=True)
        else:
            print(f"Connection failed with error code: {error_code}")
            self.disconnect()
            return        

    def on_successful_connection(self, is_connecting=False):
        connection_message = ["connect", self.username]
        connection_message = JSONEncoder().encode(connection_message).encode("utf-8")

        events = selectors.EVENT_WRITE | selectors.EVENT_READ

        data = types.SimpleNamespace(
            is_connecting=is_connecting,
            connid=self.username,
            inb= b"",
            outb=connection_message
        )

        sel.register(self.socket, events, data=data)
        threading.Thread(target=self.monitor_connection, args=(self.connStopEvent,)).start()

    def monitor_connection(self, stop_event):
        try:
            while not stop_event.is_set():
                if sel.get_map() and len(sel.get_map()) != 0:
                    events = sel.select(timeout=10)
                    for key, mask in events:
                        self.service_connection(key, mask)
        except KeyboardInterrupt:
            print("Caught keyboard interrupt, exiting")
        finally:
            self.disconnect()
    
    def disconnect(self):
        if self.disconnecting_mutex:
            return
        
        self.disconnecting_mutex = True
        print("Disconnecting from server.")
        self.connStopEvent.set()
        sel.unregister(self.socket)
        sel.close()
        self.socket.close()
        print("Disconnected.")

    def send_message(self, recipient, message):
        message = ["send", recipient, message]
        message = JSONEncoder().encode(message).encode("utf-8")

        key = sel.get_key(self.socket)
        data = key.data

        data.outb += message

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        
        if data.is_connecting:
            err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            
            if err == 0:
                data.is_connecting = False
            else:
                print(f"Connection failed during completion: Error {err} ({errno.errorcode.get(err)})")
                self.disconnect()
            
            return
        else:
            if mask & selectors.EVENT_READ:
                recv_data = sock.recv(1024)  # Should be ready to read
                if recv_data:
                    data.inb += recv_data

                    try:
                        decoded = data.inb.decode("utf-8")
                        decoded = JSONDecoder().decode(decoded)
                        data.inb = b""

                        if decoded[0] == "incoming message":
                            sender = decoded[1]
                            message = decoded[2]

                            print(f"\nMessage from {Fore.MAGENTA}{sender}: {Fore.CYAN}{message}{Style.RESET_ALL}")

                    except ValueError:
                        pass

                else:
                    print(f"Closing connection {data.connid}")
                    sel.unregister(sock)
                    sock.close()
            if mask & selectors.EVENT_WRITE:
                if data.outb:
                    sent = sock.send(data.outb)  # Should be ready to write
                    data.outb = data.outb[sent:]