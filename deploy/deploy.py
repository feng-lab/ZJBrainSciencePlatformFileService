import argparse
import json
import subprocess
from pathlib import Path

from build_image import build_tag

cwd = Path(__file__).parent


remote_script = """
    set -euo pipefail
    export PORT={port}
    export FILE_DIR={file_dir}
    export LOG_DIR={log_dir}
    export IMAGE_TAG={image_tag}
    docker compose -f {compose_file} up -d
"""


def main(env: str, registry_name: str, version: str) -> None:
    config_path = cwd / "config.json"
    config = json.loads(config_path.read_bytes())
    deploy_config = config["deploy"]["common"] | config["deploy"][env]

    ssh_identity_args = ["-i", f"~/.ssh/{deploy_config['identity']}"]
    ssh_destination = f"{deploy_config['user']}@{deploy_config['host']}"

    # 上传 docker-compose.yaml
    subprocess.run(
        ["scp", *ssh_identity_args, str(cwd / "docker-compose.yaml"), f"{ssh_destination}:{deploy_config['file']}"],
        check=True,
    )

    # 运行部署脚本
    registry = config["registries"][registry_name]
    image_tag = build_tag(registry["registry"], registry["user"], config["image"]["repo"], version)
    remote_cmd = remote_script.format(
        port=deploy_config["PORT"],
        file_dir=deploy_config["FILE_DIR"],
        log_dir=deploy_config["LOG_DIR"],
        image_tag=image_tag,
        compose_file=deploy_config["file"],
    )
    subprocess.run(["ssh", *ssh_identity_args, ssh_destination, "bash"], input=remote_cmd.encode("UTF-8"), check=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("env")
    parser.add_argument("registry")
    parser.add_argument("version")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.env, args.registry, args.version)
