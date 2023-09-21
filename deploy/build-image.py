import os
import subprocess
from datetime import datetime
from pathlib import Path

CWD: Path = Path(os.environ.get("CWD", Path(__file__).parent.parent)).absolute()
DOCKER_FILE: Path = Path(os.environ.get("DOCKER_FILE", CWD / "deploy" / "Dockerfile")).absolute()
DOCKER_USER: str = str(os.environ.get("DOCKER_USER", "cnife"))
DOCKER_IMAGE_REPO: str = str(os.environ.get("DOCKER_IMAGE_REPO", "zjbs-file-server"))


def main() -> None:
    current_time = datetime.now().strftime("%Y%m%d-%H%M%S")
    git_hash = subprocess.run(
        ["git", "-C", str(CWD), "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    image_version = f"{current_time}-{git_hash}"
    time_hash_tag = f"{DOCKER_USER}/{DOCKER_IMAGE_REPO}:{image_version}"
    latest_tag = f"{DOCKER_USER}/{DOCKER_IMAGE_REPO}:latest"

    subprocess.run(
        [
            "docker",
            "build",
            "--file",
            str(DOCKER_FILE),
            "--tag",
            time_hash_tag,
            "--tag",
            latest_tag,
            "--push",
            str(CWD),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
