import subprocess, os, time
import argparse
from dotenv import load_dotenv


parser = argparse.ArgumentParser(description="Obtains .env path")
parser.add_argument("--env", help="The path to .env")
args = parser.parse_args()

load_dotenv(args.env)


def get_env_var(
    key, type: type, default=None
):  # TODO implement cool env var get function
    try:
        return type(os.environ[key])
    except Exception as e:
        print(f"Environmental Variable Error: {e}", flush=True)
        if default:
            return default
        exit(1)


SERVER_DOCKER_DIR = get_env_var("SERVER_DOCKER_DIR", str, "/snap/bin/docker")
SERVER_DOCKER_CONTAINER = get_env_var("SERVER_DOCKER_CONTAINER", str)
SERVER_MC_RCON_PASSWORD = get_env_var("SERVER_MC_RCON_PASSWORD", str)
TIMESTAMP_FILE_PATH = get_env_var(
    "TIMESTAMP_FILE_PATH", str, "/run/mc-server-regulator-timestamp"
)


def get_string_from_file(path):
    with open(path, "r") as file:
        return file.read()


def main():
    # Capture the full result object instead of just stdout immediately
    result = subprocess.run(
        [
            SERVER_DOCKER_DIR,
            "exec",
            SERVER_DOCKER_CONTAINER,
            "rcon-cli",
            "--password",
            SERVER_MC_RCON_PASSWORD,
            "list",
        ],
        capture_output=True,
        text=True,
    )
    listOutput = result.stdout

    # Check if the output is empty and log the error if it is
    if not listOutput:
        print(
            "Error: listOutput is empty. The docker command may have failed.",
            flush=True,
        )
        print(f"Stderr output: {result.stderr}", flush=True)
        return

    print(listOutput, flush=True)

    # Use a try-except here just in case the output is shorter than expected
    try:
        players_are_online = listOutput[10] != "0"
    except IndexError:
        print(
            f"Error: listOutput was too short to check index 10. Output: '{listOutput}'",
            flush=True,
        )
        return

    if players_are_online:
        print("Trying to remove time file.", flush=True)
        try:
            os.remove(TIMESTAMP_FILE_PATH)
        except FileNotFoundError:
            pass
    else:
        if os.path.exists(TIMESTAMP_FILE_PATH):
            elapsed_time = time.time() - int(get_string_from_file(TIMESTAMP_FILE_PATH))
            print(elapsed_time / 60, " minutes of inactivity logged.", flush=True)
            if elapsed_time >= 1800:
                print("Shutting down due to inactivity.", flush=True)
                subprocess.run(["sudo", "poweroff"])
        else:
            print("Logging first time of inactivity.", flush=True)
            with open(TIMESTAMP_FILE_PATH, "w") as f:
                f.write(str(int(time.time())))


if __name__ == "__main__":
    main()
