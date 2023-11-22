import json
import re
import subprocess
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

cwd = Path(__file__).parent


def new_main(config_path: Path, registry_name: str, push: bool) -> None:
    config = json.loads(config_path.read_bytes())
    for registry in config["registries"]:
        if registry["name"] == registry_name:
            break
    else:
        raise ValueError(f"registry '{registry_name}' not found")

    versions = []
    for version in config["versions"]:
        if re.search(r"\{git_hash(:\S+)?}", version):
            git_hash = subprocess.run(
                ["git", "-C", str(cwd), "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True, check=True
            ).stdout.strip()
            version = version.format(git_hash=git_hash)
        if "%" in version:
            version = datetime.now().strftime(version)
        versions.append(version)

    registry_url = "" if registry["registry"] == "default" else registry["registry"] + "/"
    user_name = "" if registry["user"] is None else registry["user"] + "/"
    tags = [f"{registry_url}{user_name}{config['repo']}:{version}" for version in versions]

    docker_cmd = ["docker", "build", "--file", str(cwd / config["dockerfile"])]
    for tag in tags:
        docker_cmd.extend(["--tag", tag])
    if push:
        docker_cmd.append("--push")
    docker_cmd.append(str(cwd / config["cwd"]))
    subprocess.run(docker_cmd, check=True)


def parse_args() -> Namespace:
    parser = ArgumentParser(description="构建镜像", formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("registry", help="推送到哪个docker registry")
    parser.add_argument("--config", "-c", type=Path, default=cwd / "build-image-config.json", help="配置文件")
    parser.add_argument("--push", "-p", action="store_true", default=False, help="是否推送镜像")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    new_main(args.config, args.registry, args.push)
