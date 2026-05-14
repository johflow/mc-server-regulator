import subprocess, os, time

TIMESTAMP_FILE_PATH = "/home/gal/tools/server-regulator/TIMESTAMP_FILE"

def get_string_from_file(path):
    with open(path, 'r') as file:
        return file.read()

def main():
    # Capture the full result object instead of just stdout immediately
    result = subprocess.run(["docker", "exec", "eternal-mc", "rcon-cli", "--password", "1935d797a5608d27286734fb",  "list"], capture_output=True, text=True)
    listOutput = result.stdout
    
    # Check if the output is empty and log the error if it is
    if not listOutput:
        print("Error: listOutput is empty. The docker command may have failed.", flush=True)
        print(f"Stderr output: {result.stderr}", flush=True)
        return
        
    print(listOutput, flush=True)
    
    # Use a try-except here just in case the output is shorter than expected
    try:
        players_are_online = listOutput[10] != '0'
    except IndexError:
        print(f"Error: listOutput was too short to check index 10. Output: '{listOutput}'", flush=True)
        return

    if players_are_online:
        print("Trying to remove time file.", flush=True)
        try:
            os.remove(TIMESTAMP_FILE_PATH)
        except FileNotFoundError:
            pass
    else:
        if(os.path.exists(TIMESTAMP_FILE_PATH)):
            elapsed_time = time.time() - int(get_string_from_file(TIMESTAMP_FILE_PATH))
            print(elapsed_time/60, " minutes of inactivity logged.", flush=True)
            if elapsed_time >= 1800: 
                os.remove(TIMESTAMP_FILE_PATH)
                print("Shutting down due to inactivity.", flush=True)
                subprocess.run(["sudo", "poweroff"])
        else:
            print("Logging first time of inactivity.", flush=True)
            with open(TIMESTAMP_FILE_PATH, "w") as f:
                f.write(str(int(time.time())))


if __name__ == "__main__":
    main()
