import subprocess
import time
import wakeonlan
import socket
import sys
from minecraft.networking.server import Server
from minecraft.networking.packets import serverbound
from minecraft.networking.packets import clientbound
from minecraft.networking.types import JSON


SERVER_MAC_ADDRESS = "04:7c:16:4d:61:cb"
SERVER_PORT = 25565
SERVER_IP = "192.168.1.72"
COOLDOWN_PERIOD = 30
TIMEOUT_PERIOD = 30
SERVER_BOOT_PERIOD = 300
SPOOFING_SERVER = False


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


def handle_new_player_connection(connection):
    print(f"A new client has connected from address: {connection.address}.")
    
    def on_login_attempt(login_packet):
        global SPOOFING_SERVER
        player_name = login_packet.username
        print(f"Player '{player_name}' is attempting to log in.")
        reason_message = {
            "text": "You've woken the server! Please try again in 2 minutes."
        }

        disconnect_packet = clientbound.login.DisconnectPacket(json_data=JSON.dump(reason_message))
        connection.write_packet(disconnect_packet)
        SPOOFING_SERVER = False

    connection.register_packet_listener(on_login_attempt, serverbound.login.LoginStartPacket)


def main():
    server = Server("0.0.0.0", SERVER_PORT)
    server.register_join_handler(handle_new_player_connection)
    try:
        while True:
            if not server_awake():
                spoof_server_mac()
                server.start()
                SPOOFING_SERVER = True
                while SPOOFING_SERVER:
                    time.sleep(1)
                server.stop()
                wake_and_restore()
                boot_start_time = time.time()
                while not server_awake(timeout=5):  # faster polling while booting
                    if time.time() - boot_start_time > SERVER_BOOT_PERIOD:
                        print(f"Server failed to start within {SERVER_BOOT_PERIOD} seconds!")
                        break
                    time.sleep(5)
            else:
                time.sleep(COOLDOWN_PERIOD)
    finally:
        # Always restore MAC on exit
        restore_original_mac()
        print("Exited cleanly.", flush=True)


if __name__ == "__main__":
    main()

