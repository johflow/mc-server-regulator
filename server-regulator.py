import subprocess
import time
import wakeonlan
import socket
import sys

SERVER_MAC_ADDRESS = "04:7c:16:4d:61:cb"
SERVER_PORT = 25565
SERVER_IP = "192.168.1.72"
COOLDOWN_PERIOD = 30
SERVER_BOOT_PERIOD = 120
TIMEOUT_PERIOD = 30
LISTEN_TIMEOUT = 60  # how long wait_and_listen waits before giving up


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


def wait_and_listen() -> bool:
    """Return True if a connection was accepted, False on timeout/error."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", SERVER_PORT))
            s.listen()
            s.settimeout(LISTEN_TIMEOUT)
            print("Listener active, waiting for a connection...", flush=True)

            connection, address = s.accept()
            connection.close()
            print(f"Connection from {address}. Waking server.", flush=True)
            return True
        except socket.timeout:
            print("Listener timed out, retrying...", flush=True)
            return False
        except Exception as e:
            print(f"An error occurred: {e}", flush=True)
            return False


def main():
    try:
        while True:
            if not server_awake():
                spoof_server_mac()
                got_connection = wait_and_listen()
                if got_connection:
                    wake_and_restore()
                    while not server_awake(timeout=5):  # faster polling while booting
                        time.sleep(5)
                else:
                    # No incoming connection — restore MAC but do NOT wake the server.
                    restore_original_mac()
            else:
                time.sleep(COOLDOWN_PERIOD)
    finally:
        # Always restore MAC on exit
        restore_original_mac()
        print("Exited cleanly.", flush=True)


if __name__ == "__main__":
    main()

