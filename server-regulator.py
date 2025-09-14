import subprocess
import time
import wakeonlan
import socket
import sys
import json

# --- Constants ---
SERVER_MAC_ADDRESS = "04:7c:16:4d:61:cb"
SERVER_PORT = 25565
SERVER_IP = "192.168.1.72"
COOLDOWN_PERIOD = 30
TIMEOUT_PERIOD = 30
SERVER_BOOT_PERIOD = 300
LISTEN_TIMEOUT = 60
CUSTOM_KICK_MESSAGE = "§eThe server is waking up... §aPlease try again in 2 minutes!"

# --- Helper Functions (unchanged, except for the new _read_varint_from_socket) ---

def restore_original_mac():
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "down"])
    subprocess.run(["sudo", "macchanger", "-p", "eth0"])
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "up"])
    print("Original MAC address restored.", flush=True)

def wake_and_restore():
    wakeonlan.send_magic_packet(SERVER_MAC_ADDRESS)
    print("Sent wake on lan packet.", flush=True)
    restore_original_mac()

def spoof_server_mac():
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "down"])
    subprocess.run(["sudo", "macchanger", "-m", SERVER_MAC_ADDRESS, "eth0"])
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "up"])
    print(f"Spoofed MAC address to {SERVER_MAC_ADDRESS}.", flush=True)

def server_awake(timeout=TIMEOUT_PERIOD) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(timeout)
            s.connect((SERVER_IP, SERVER_PORT))
            print("Server is online.", flush=True)
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            print("Server is offline.", flush=True)
            return False


def recv_exact(conn, n):
    data = bytearray()
    while len(data) < n:
        new_bytes = conn.recv(n - len(data))
        if not new_bytes:
            raise IOError("connection closed")
        data.extend(new_bytes)
    return bytes(data)


def recv_vlq_bytes(conn):
    num_bytes = 0
    another_byte = True
    value = 0

    while another_byte:
        byte = recv_exact(conn, 1)
        byte_value = byte[0]

        var_int_piece = byte_value & 0x7f
        another_byte = (byte_value & 0x80) != 0

        value |= var_int_piece << (7 * num_bytes)
        num_bytes += 1

    return value 




def login_attempted() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", SERVER_PORT))
            s.listen()
            s.settimeout(LISTEN_TIMEOUT)
            print("Precise listener active, waiting for a JOIN attempt...", flush=True)

            connection, address = s.accept()
            with connection:
                packet_length = recv_vlq_bytes(connection)
                packet_id = recv_vlq_bytes(connection)
                client_protocol = recv_vlq_bytes(connection)
                client_address_length = recv_vlq_bytes(connection)
                client_address = recv_exact(connection, client_address_length)
                client_connection_port = recv_exact(connection, 2)
                client_connection_reason = recv_vlq_bytes(connection)
                if client_connection_reason == 2:
                    send_disconnect_packet(connection)
                    return True
        except socket.timeout:
            print("Connection timed out", flush=True)
            return False
    return False


def send_disconnect_packet(conn):
    reason_json = json.dumps({"text": CUSTOM_KICK_MESSAGE})
    reason_bytes = reason_json.encode("utf-8")
    reason_length = encode_varint(len(reason_bytes))
    packet_id = encode_varint(0x00)
    packet_data = packet_id + reason_length + reason_bytes
    packet_length = encode_varint(len(packet_data))
    conn.sendall(packet_length + packet_data)

def encode_varint(value):
    out = b""
    while True:
        temp = value & 0x7F
        value >>= 7
        if value != 0:
            out += bytes([temp | 0x80])
        else:
            out += bytes([temp])
            break
    return out



# --- MODIFIED: Main function now calls the new listener name ---
def main():
    try:
        while True:
            if not server_awake():
                spoof_server_mac()
                while not server_awake():
                    if login_attempted():
                        wakeonlan.send_magic_packet(SERVER_MAC_ADDRESS)
                        time.sleep(5)
                        break
                restore_original_mac()
                while not server_awake():
                    time.sleep(5)
            else:
                time.sleep(COOLDOWN_PERIOD)
    finally:
        restore_original_mac()
        print("Exited cleanly.", flush=True)




if __name__ == "__main__":
    main()
