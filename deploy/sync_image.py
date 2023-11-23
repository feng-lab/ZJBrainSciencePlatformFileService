import json
import subprocess
from argparse import ArgumentParser, Namespace
from pathlib import Path

from build_image import build_tag

cwd: Path = Path(__file__).parent


def main(from_registry: str, to_registry: str, version: str) -> None:
    config_path = cwd / "config.json"
    config = json.loads(config_path.read_bytes())

    from_registry, to_registry = config["registries"][from_registry], config["registries"][to_registry]
    from_tag = build_tag(from_registry["registry"], from_registry["user"], config["image"]["repo"], version)
    to_tag = build_tag(to_registry["registry"], to_registry["user"], config["image"]["repo"], version)

    subprocess.run(["docker", "pull", from_tag], check=True)
    subprocess.run(["docker", "tag", from_tag, to_tag], check=True)
    subprocess.run(["docker", "push", to_tag], check=True)


def parse_args() -> Namespace:
    parser = ArgumentParser(description="同步镜像")
    parser.add_argument("from_registry", help="从哪个registry同步")
    parser.add_argument("to_registry", help="同步到哪个registry")
    parser.add_argument("version", help="镜像版本")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args.from_registry, args.to_registry, args.version)
