import argparse
import json
import subprocess
from pathlib import Path
from textwrap import dedent


def main(env: str, version: str) -> None:
    env_config_path = Path(__file__).parent / "envs" / f"{env}.json"
    config = json.loads(env_config_path.read_bytes())

    ssh_identity_args = ["-i", f"~/.ssh/{config['ssh']['identity']}"]
    ssh_destination = f"{config['ssh']['user']}@{config['ssh']['host']}"

    docker_compose_path = Path(__file__).parent / "docker-compose.yaml"
    subprocess.run(
        ["scp", *ssh_identity_args, str(docker_compose_path), f"{ssh_destination}:{config['docker-compose']['file']}"],
        check=True,
    )

    remote_cmd = dedent(
        f"""
        set -euo pipefail
        export PORT={config["docker-compose"]["PORT"]}
        export FILE_DIR={config["docker-compose"]["FILE_DIR"]}
        export LOG_DIR={config["docker-compose"]["LOG_DIR"]}
        export IMAGE_VERSION={version}
        docker compose -f {config["docker-compose"]["file"]} up -d
    """
    )
    subprocess.run(["ssh", *ssh_identity_args, ssh_destination, "bash"], input=remote_cmd.encode("UTF-8"), check=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("env", type=str, choices=["testing", "production"])
    parser.add_argument("version", type=str)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.env, args.version)
