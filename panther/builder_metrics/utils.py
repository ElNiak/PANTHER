"""Utilities for measuring build artifacts and Docker images."""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_directory_size_mb(directory: Path) -> float:
    """From typing import Dict, List, Optional, Tuple, TupleGet the total size of a directory in megabytes.

    Args:
            directory: Path to the directory

    Returns:
            Size in megabytes
    """
    if not directory.exists() or not directory.is_dir():
        return 0.0

    total_size = 0
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            try:
                total_size += file_path.stat().st_size
            except (OSError, FileNotFoundError):
                # Skip files that can't be accessed
                pass

    return total_size / (1024 * 1024)  # Convert to MB


def get_docker_image_size_mb(image_name: str) -> Optional[float]:
    """Get the size of a Docker image in megabytes.

    Args:
        image_name: Name or ID of the Docker image

    Returns:
        Size in megabytes or None if image not found
    """
    try:
        # Use docker inspect to get image size
        result = subprocess.run(
            ["docker", "inspect", image_name],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        # Parse the JSON response
        inspect_data = json.loads(result.stdout)
        if not inspect_data:
            return None

        # Get size from the first (and should be only) image
        image_data = inspect_data[0]
        size_bytes = image_data.get("Size", 0)

        return size_bytes / (1024 * 1024)  # Convert to MB

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        FileNotFoundError,
        KeyError,
    ):
        return None


def get_docker_image_info(image_name: str) -> Optional[Dict]:
    """Get detailed information about a Docker image.

    Args:
        image_name: Name or ID of the Docker image

    Returns:
        Dictionary with image information or None if not found
    """
    try:
        # Use docker inspect to get full image info
        result = subprocess.run(
            ["docker", "inspect", image_name],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return None

        # Parse the JSON response
        inspect_data = json.loads(result.stdout)
        if not inspect_data:
            return None

        image_data = inspect_data[0]

        return {
            "id": image_data.get("Id", ""),
            "size_bytes": image_data.get("Size", 0),
            "size_mb": image_data.get("Size", 0) / (1024 * 1024),
            "virtual_size_bytes": image_data.get("VirtualSize", 0),
            "virtual_size_mb": image_data.get("VirtualSize", 0) / (1024 * 1024),
            "created": image_data.get("Created", ""),
            "architecture": image_data.get("Architecture", ""),
            "os": image_data.get("Os", ""),
        }

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        FileNotFoundError,
        KeyError,
    ):
        return None


def find_latest_wheel(
    dist_dir: Path, package_name: str
) -> Optional[Tuple[Path, float]]:
    """Find the latest wheel file and its size.

    Args:
        dist_dir: Distribution directory
        package_name: Package name to search for

    Returns:
        Tuple of (wheel_path, size_mb) or None if not found
    """
    if not dist_dir.exists():
        return None

    # Find wheel files for the package
    pattern = f"{package_name.replace('-', '_')}-*.whl"
    wheel_files = list(dist_dir.glob(pattern))

    if not wheel_files:
        # Try with the original package name
        pattern = f"{package_name}-*.whl"
        wheel_files = list(dist_dir.glob(pattern))

    if not wheel_files:
        return None

    # Get the most recently created wheel
    latest_wheel = max(wheel_files, key=lambda p: p.stat().st_mtime)
    size_mb = latest_wheel.stat().st_size / (1024 * 1024)

    return latest_wheel, size_mb


def get_file_size_mb(file_path: Path) -> float:
    """Get the size of a file in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        Size in megabytes
    """
    if not file_path.exists() or not file_path.is_file():
        return 0.0

    try:
        return file_path.stat().st_size / (1024 * 1024)
    except (OSError, FileNotFoundError):
        return 0.0


def list_docker_images_with_pattern(pattern: str) -> List[str]:
    """List Docker images matching a pattern.

    Args:
        pattern: Pattern to match in image names

    Returns:
        List of image names
    """
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return []

        # Filter images that contain the pattern
        images = []
        for line in result.stdout.strip().split("\n"):
            if line and pattern.lower() in line.lower():
                images.append(line)

        return images

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        return []


def cleanup_build_artifacts(project_root: Path) -> Dict[str, float]:
    """Clean up build artifacts and return size information.

    Args:
        project_root: Root directory of the project

    Returns:
        Dictionary with cleanup information
    """
    artifacts = {
        "build": project_root / "build",
        "dist": project_root / "dist",
        "htmlcov": project_root / "htmlcov",
        "site": project_root / "site",
        "docs": project_root / "docs",
    }

    cleanup_info = {}

    for name, path in artifacts.items():
        if path.exists():
            size_mb = get_directory_size_mb(path)
            cleanup_info[f"{name}_size_mb"] = size_mb
        else:
            cleanup_info[f"{name}_size_mb"] = 0.0

    return cleanup_info
