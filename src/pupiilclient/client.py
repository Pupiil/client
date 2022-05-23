#!/usr/bin/env python3

import sys
import socket
import selectors
import traceback

from pupiilcommon import libclient, MacAuxClass

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
            content=dict(action=action, value=MacAuxClass.MacAux().get_machine_info()),
        )
    else:
        return dict(
            type="binary/custom-client-binary-type",
            encoding="binary",
            content=bytes(action + value, encoding="utf-8"),
        )


def start_connection(host, port, request, client):
    addr = (host, port)
    print(f"[CLIENT::CLIENT] Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((client[0], client[1]))
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = libclient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)


def main():

    config = {
        "server_ip": "127.42.0.1",
        "server_port": 5201,
        "client_ip": "127.1.1.1",
        "client_port": 6000,
        "action": "add",
        "value": ""
    }

    host, port = config['server_ip'], config["server_port"]
    action, value = config["action"], config["value"]
    request = create_request(action, value)
    start_connection(host, port, request, (config["client_ip"], config["client_port"]))

    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                message = key.data
                try:
                    message.process_events(mask)
                except Exception:
                    print(
                        "[CLIENT::CLIENT] Main: error: exception for",
                        f"{message.addr}:\n{traceback.format_exc()}",
                    )
                    message.close()
            # Check for a socket being monitored to continue.
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("[CLIENT::CLIENT] caught keyboard interrupt, exiting")
    finally:
        sel.close()


if __name__ == "__main__":
    main()
