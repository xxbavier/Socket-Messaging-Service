import os
import time

from client import Client
from server import Server
import sys

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 65432 # Port to listen on (non-privileged ports are > 1023)

def main():
    #os.system('cls' if os.name == 'nt' else 'clear')
    #time.sleep(1)

    if not len(sys.argv) == 2:
        print("Usage: python main-client.py <Username>")
        sys.exit(1)

    client = Client(HOST, PORT, sys.argv[1])
    client.connect()

    while True:
        recipient = input("Please specify the recipient's username or enter 'q' to quit: ")

        if recipient == 'q':
            client.disconnect()
            break
        else:
            message = input("Enter your message: ")
            client.send_message(recipient, message)

    client.disconnect()

    #message = input("Enter your message: ")

    #client.send_message("Client2", message)

    #client.create_gui()


if __name__ == "__main__":
    main()