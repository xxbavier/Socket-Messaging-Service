import os
import time

from client import Client
from server import Server

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432  # Port to listen on (non-privileged ports are > 1023)

def main():
    #os.system('cls' if os.name == 'nt' else 'clear')
    #time.sleep(1)
    
    server = Server(HOST, PORT)
    server.start()



if __name__ == "__main__":
    main()