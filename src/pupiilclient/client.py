#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback

import lib.libclient
from lib.MacAuxClass import MacAux

sel = selectors.DefaultSelector()


def create_request(action, value):
    if action == "search":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, value=value),
        )
    elif action == "add":
        return dict(
            type="text/json",
            encoding="utf-8",
            content=dict(action=action, value=MacAux().get_machine_info()),
        )
    else:
        return dict(
            type="binary/custom-client-binary-type",
            encoding="binary",
            content=bytes(action + value, encoding="utf-8"),
        )


def start_connection(host, port, request, client):
    for index in range(0, 10):
        addr = (host, port)
        print(f"starting connection to {addr}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((client[0], client[1] + index))
        sock.setblocking(False)
        sock.connect_ex(addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        message = lib.libclient.Message(sel, sock, addr, request)
        sel.register(sock, events, data=message)


if len(sys.argv) == 6:
    sys.argv.append("")
elif len(sys.argv) < 5:
    print(
        f"usage: {sys.argv[0]} <server_ip> <server_port> <client_ip> <client_port> <action> <value>"
    )
    sys.exit(1)

host, port = sys.argv[1], int(sys.argv[2])
action, value = sys.argv[5], sys.argv[6]
request = create_request(action, value)
start_connection(host, port, request, (sys.argv[3], int(sys.argv[4])))

try:
    while True:
        events = sel.select(timeout=1)
        for key, mask in events:
            message = key.data
            try:
                message.process_events(mask)
            except Exception:
                print(
                    "main: error: exception for",
                    f"{message.addr}:\n{traceback.format_exc()}",
                )
                message.close()
        # Check for a socket being monitored to continue.
        if not sel.get_map():
            break
except KeyboardInterrupt:
    print("caught keyboard interrupt, exiting")
finally:
    sel.close()