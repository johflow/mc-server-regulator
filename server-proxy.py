import subprocess
import time
import socket
import json
import io
import os
import wakeonlan


def get_env_var(key, type: type, default=None):
    try:
        return type(os.environ[key])
    except Exception as e:
        print(f"Environmental Variable Error: {e}", flush=True)
        if default:
            return default
        exit(1)


SERVER_IP = get_env_var("SERVER_IP", str, "192.168.1.72")
SERVER_DOMAIN = get_env_var("SERVER_DOMAIN", str)
SERVER_MAC_ADDRESS = get_env_var("SERVER_MAC_ADDRESS", str)
CUSTOM_KICK_MESSAGE = get_env_var(
    "CUSTOM_KICK_MESSAGE",
    str,
    "§eThe server is waking up... §aPlease try again in 2 minutes!",
)
COOLDOWN_PERIOD = get_env_var("COOLDOWN_PERIOD", int, 30)
SERVER_PORT = get_env_var("SERVER_PORT", int, 25565)
LISTEN_TIMEOUT = get_env_var("LISTEN_TIMEOUT", int, 60)


def add_ip_alias():
    subprocess.run(["sudo", "ip", "addr", "add", SERVER_IP + "/24", "dev", "eth0"])
    subprocess.run(["sudo", "arping", "-U", "-c", "3", "-I", "eth0", SERVER_IP])


def remove_ip_alias():
    subprocess.run(["sudo", "ip", "addr", "del", SERVER_IP + "/24", "dev", "eth0"])


def wake_server():
    wakeonlan.send_magic_packet(SERVER_MAC_ADDRESS)
    print("Sent wake on lan packet.", flush=True)


def server_awake() -> bool:
    print("Checking if server is awake", flush=True)
    try:
        result = subprocess.run(
            ["sudo", "arping", "-c", "1", "-w", "2", "-I", "eth0", SERVER_IP],
            capture_output=True,
            text=True,
        )
        return SERVER_MAC_ADDRESS.lower() in result.stdout.lower()
    except Exception as e:
        print(f"Error checking server state: {e}", flush=True)
        return False


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

        vlq_data = byte_value & 0x7F
        another_byte = (byte_value & 0x80) != 0

        data |= vlq_data << (7 * num_bytes)
        num_bytes += 1
        if num_bytes > 5:
            raise ValueError("VLQ is longer than 5 bytes & shouldn't be!")

    return data


def is_valid_join_address(address):
    decoded = address.decode("utf-8", errors="ignore")
    return SERVER_DOMAIN in decoded


def login_attempted() -> bool:  # clean up
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", SERVER_PORT))
            s.listen()
            s.settimeout(int(LISTEN_TIMEOUT))
            print("Precise listener active, waiting for a JOIN attempt...", flush=True)

            while True:
                connection, address = s.accept()
                print(f"Connection made with {address}!", flush=True)
                connection.settimeout(0.5)
                with connection:
                    try:
                        with connection.makefile("rb") as socket_stream:
                            packet_length = get_vlq_bytes(socket_stream)
                            packet_data = safe_read(socket_stream, packet_length)
                        stream_packet_data = io.BytesIO(packet_data)

                        packet_id = get_vlq_bytes(stream_packet_data)
                        client_protocol = get_vlq_bytes(stream_packet_data)
                        client_address_length = get_vlq_bytes(stream_packet_data)
                        client_address = safe_read(
                            stream_packet_data, client_address_length
                        )
                        client_connection_port = safe_read(stream_packet_data, 2)
                        client_connection_reason = get_vlq_bytes(stream_packet_data)
                        print(client_connection_reason, flush=True)
                        if client_connection_reason == 2:
                            print(
                                f"Server join request from following packet: {packet_id}, {client_protocol}, {client_address}, {client_connection_port}, {client_connection_reason}"
                            )
                            if is_valid_join_address(client_address):
                                send_disconnect_packet(connection)
                                print("Disconnect packet sent!", flush=True)
                                return True
                    except (IOError, OSError, ValueError) as e:
                        print(f"Handshake failed early: {e}", flush=True)
                        continue
        except socket.timeout:
            print("Socket timed out", flush=True)
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


def wait_for_server_boot():  # Fix magic numbers
    i = 0
    while not server_awake() and i < 60:
        i += 1
        time.sleep(5)


def satisy_preconditions():
    remove_ip_alias()


def main():
    satisy_preconditions()
    try:
        while True:
            if not server_awake():
                add_ip_alias()
                while not server_awake():
                    if login_attempted():
                        wake_server()
                        time.sleep(5)
                        break
                remove_ip_alias()
                wait_for_server_boot()
            else:
                time.sleep(COOLDOWN_PERIOD)
    finally:
        remove_ip_alias()
        print("Exited cleanly.", flush=True)


if __name__ == "__main__":
    main()
