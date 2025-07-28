import subprocess, time, wakeonlan, socket
LOCAL_MAC_ADDRESS = subprocess.run("ip addr | grep link/ether | awk '{ print $2 }'", shell=True, capture_output=True, text=True).stdout.strip()
SERVER_MAC_ADDRESS = "04:7c:16:4d:61:cb"


def wake_and_restore():
    wakeonlan.send(SERVER_MAC_ADDRESS)
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "down"])
    subprocess.run(["sudo", "macchanger", "-p", "eth0"])
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "up"])


def spoof_server_mac():
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "down"])
    subprocess.run(["sudo", "macchanger", "-m", SERVER_MAC_ADDRESS, "eth0"])
    subprocess.run(["sudo", "ip", "link", "set", "eth0", "up"])
    
def main():
    spoof_server_mac()
    socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_tcp.bind(("0.0.0.0", 25565))
    socket_tcp.listen()
    while True:
        try:
            connection, address = socket_tcp.accept()
            print(address, " attempted to connect to the server")
            wake_and_restore()
            connection.close()
            break
        except:
            print("Error accepting connection!")
        finally:    
            socket_tcp.close()






if __name__ == "__main__":
	main()
