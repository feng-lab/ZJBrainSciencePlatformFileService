import json
import re
import subprocess
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

cwd = Path(__file__).parent


def build_and_push(push: bool, registry_name: str) -> None:
    config_path = cwd / "config.json"
    config = json.loads(config_path.read_bytes())

    registry = config["registries"][registry_name]
    tags = [
        build_tag(registry["registry"], registry["user"], config["image"]["repo"], resolve_version(version_template))
        for version_template in config["build"]["versions"]
    ]

    docker_cmd = build_docker_cmd(cwd / config["build"]["dockerfile"], cwd / config["build"]["context"], tags, push)
    subprocess.run(docker_cmd, check=True)


def build_tag(registry: str | None, user: str | None, repo: str, version: str) -> str:
    registry_part = f"{registry}/" if registry else ""
    user_part = f"{user}/" if user else ""
    return f"{registry_part}{user_part}{repo}:{version}"


def resolve_version(version: str) -> str:
    if re.search(r"\{git_hash(:\S+)?}", version):
        git_hash = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        version = version.format(git_hash=git_hash)
    if "%" in version:
        version = datetime.now().strftime(version)
    return version


def build_docker_cmd(dockerfile: Path, context: Path, tags: list[str], push: bool) -> list[str]:
    docker_cmd = ["docker", "build", "--file", str(dockerfile.absolute())]
    for tag in tags:
        docker_cmd.append("--tag")
        docker_cmd.append(tag)
    if push:
        docker_cmd.append("--push")
    docker_cmd.append(str(context.absolute()))
    return docker_cmd


def parse_args() -> Namespace:
    parser = ArgumentParser(description="构建并推送镜像", formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("--push", "-p", action="store_true", default=False, help="是否推送镜像")
    parser.add_argument("registry", help="推送到哪个docker registry")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_and_push(args.push, args.registry)
