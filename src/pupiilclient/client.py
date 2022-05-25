#!/usr/bin/env python3

import socket
import selectors
import traceback
import threading

import pupiilcommon


def client_create_request(action, value):
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
            content=dict(
                action=action,
                value=pupiilcommon.MacAuxClass.MacAux().get_machine_info(),
            ),
        )
    else:
        return dict(
            type="binary/custom-client-binary-type",
            encoding="binary",
            content=bytes(action + value, encoding="utf-8"),
        )


def client_start_connection(sel, host, port, request, client):
    addr = (host, port)
    print(f"[CLIENT::CLIENT] Starting connection to {addr}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((client[0], client[1]))
    sock.setblocking(False)
    sock.connect_ex(addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    message = pupiilcommon.LibClient.Message(sel, sock, addr, request)
    sel.register(sock, events, data=message)


def server_accept_wrapper(sel, sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)
    message = pupiilcommon.LibRecvFrame.Message(sel, conn, addr)
    sel.register(conn, selectors.EVENT_READ, data=message)


def recognition_to_client__server_thread(shared_state, shared_state_lock):

    recognition_to_client_sel = selectors.DefaultSelector()

    config = {
        "host": "127.46.75.34",
        "port": 6049,
    }

    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Avoid bind() exception: OSError: [Errno 48] Address already in use
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind((config["host"], config["port"]))
    lsock.listen()
    print(f"Listening on {(config['host'], config['port'])}")
    lsock.setblocking(False)
    recognition_to_client_sel.register(lsock, selectors.EVENT_READ, data=None)

    print(
        "\n[PUPIIL_CLIENT::CLIENT::recognition_to_client__server_thread] Connection Established\n"
    )

    try:
        while True:
            events = recognition_to_client_sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    server_accept_wrapper(recognition_to_client_sel, key.fileobj)
                else:
                    message = key.data
                    try:
                        message.process_events(mask)
                    except Exception:
                        print(
                            f"Main: Error: Exception for {message.addr}:\n"
                            f"{traceback.format_exc()}"
                        )
                        message.close()
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        recognition_to_client_sel.close()


def client_to_server__client_thread(shared_state, shared_state_lock):

    client_to_server_sel = selectors.DefaultSelector()

    config = {
        "server_ip": "127.42.0.1",
        "server_port": 5205,
        "client_ip": "127.1.1.2",
        "client_port": 6135,
        "action": "add",
        "value": "",
    }

    request = client_create_request(config["action"], config["value"])
    client_start_connection(
        client_to_server_sel,
        config["server_ip"],
        config["server_port"],
        request,
        (config["client_ip"], config["client_port"]),
    )

    print(
        "\n[PUPIIL_CLIENT::CLIENT::client_to_server__client_thread] Connection Established\n"
    )

    try:
        while True:
            events = client_to_server_sel.select(timeout=1)
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
            if not client_to_server_sel.get_map():
                break
    except KeyboardInterrupt:
        print("[CLIENT::CLIENT] caught keyboard interrupt, exiting")
    finally:
        client_to_server_sel.close()


def client_to_data__client_thread(shared_state, shared_state_lock):

    client_to_data_sel = selectors.DefaultSelector()

    config = {
        "data_ip": "127.72.1.1",
        "data_port": 6052,
        "client_ip": "127.1.1.1",
        "client_port": 6206,
        "action": "",
        "value": "",
    }

    host, port = config["data_ip"], config["data_port"]
    action, value = config["action"], config["value"]
    request = client_create_request(action, value)
    client_start_connection(
        client_to_data_sel,
        host,
        port,
        request,
        (config["client_ip"], config["client_port"]),
    )

    print(
        "\n[PUPIIL_CLIENT::CLIENT::client_to_data__client_thread] Connection Established\n"
    )

    try:
        while True:
            events = client_to_data_sel.select(timeout=1)
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
            if not client_to_data_sel.get_map():
                break
    except KeyboardInterrupt:
        print("[CLIENT::CLIENT] caught keyboard interrupt, exiting")
    finally:
        client_to_data_sel.close()


def main():

    shared_state = {}
    shared_state_lock = threading.Lock()

    threads = [
        recognition_to_client__server_thread,
        client_to_server__client_thread,
        client_to_data__client_thread,
    ]

    thread_states = [
        threading.Thread(
            target=node_to_node_thread, args=(shared_state, shared_state_lock)
        )
        for node_to_node_thread in threads
    ]

    # Start threads
    for thread in thread_states:
        thread.start()

    # We won't ever reach this state unless all the threads above
    # close themselves
    for thread in thread_states:
        thread.join()


if __name__ == "__main__":
    main()
