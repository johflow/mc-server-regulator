import subprocess
import time
import wakeonlan
import socket
import sys
import json
import io
import threading

SERVER_MAC_ADDRESS = "04:7c:16:4d:61:cb"
SERVER_PORT = 25565
SERVER_IP = "192.168.1.72"
PI_IP = "192.168.1.64"
COOLDOWN_PERIOD = 30
TIMEOUT_PERIOD = 30
SERVER_BOOT_PERIOD = 300
LISTEN_TIMEOUT = 60
CUSTOM_KICK_MESSAGE = "§eThe server is waking up... §aPlease try again in 2 minutes!"


def restore_original_state():
    restore_original_mac()
    restore_original_arp()

def restore_original_arp():
    subprocess.run(["sudo", "arping", "-A", "-c", "3", "-I", "eth0", PI_IP])
    subprocess.run(["sudo", "arping", "-U", "-c", "3", "-I", "eth0", "-s", SERVER_MAC_ADDRESS, SERVER_IP])

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
    return subprocess.run(
            ['ping', param, '1', host], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        ).returncode == 0

def safe_read(stream, n):
    data = stream.read(n)
    if not data or len(data) != n:
        raise IOError("Stream ended unexpectedly!")
    return data


def get_vlq_bytes(stream):
    num_bytes = 0
    another_byte = True
    data = 0

    while another_byte:
        byte = safe_read(stream, 1)
        byte_value = byte[0]

        vlq_data = byte_value & 0x7f
        another_byte = (byte_value & 0x80) != 0

        data |= vlq_data << (7 * num_bytes)
        num_bytes += 1
        if num_bytes > 5:
            raise ValueError(f"VLQ is longer than 5 bytes & shouldn't be!")

    return data 




def login_attempted() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", SERVER_PORT))
            s.listen()
            s.settimeout(LISTEN_TIMEOUT)
            print("Precise listener active, waiting for a JOIN attempt...", flush=True)

            connection, address = s.accept()
            print(f"Connection made with {address}!", flush=True)
            connection.settimeout(5)
            with connection:
                try:
                    socket_stream = connection.makefile('rb')
                    packet_length = get_vlq_bytes(socket_stream) 
                    packet_data = safe_read(socket_stream, packet_length)
                    stream_packet_data = io.BytesIO(packet_data)

                    packet_id = get_vlq_bytes(stream_packet_data)
                    client_protocol = get_vlq_bytes(stream_packet_data)
                    client_address_length = get_vlq_bytes(stream_packet_data)
                    client_address = safe_read(stream_packet_data, client_address_length)
                    client_connection_port = safe_read(stream_packet_data, 2)
                    client_connection_reason = get_vlq_bytes(stream_packet_data)
                    print(client_connection_reason, flush=True)
                    if client_connection_reason == 2:
                        send_disconnect_packet(connection)
                        print("Disconnect packet sent!", flush=True)
                        return True
                except (IOError, OSError) as e:
                    print(f"Handshake failed early: {e}", flush=True)
                    return False
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

def wait_for_server_boot(): #Fix magic numbers
    i = 0
    while not server_awake() and i < 60:
        i += 1
        time.sleep(5)



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
                restore_original_state()
                wait_for_server_boot()
            else:
                time.sleep(COOLDOWN_PERIOD)
    finally:
        restore_original_mac()
        print("Exited cleanly.", flush=True)




if __name__ == "__main__":
    main()

