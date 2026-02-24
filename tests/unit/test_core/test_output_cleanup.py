"""Tests for panther.core.outputs.output_cleanup."""

import pytest

from panther.core.outputs.output_cleanup import remove_empty_directories

pytestmark = [pytest.mark.unit]


class TestRemoveEmptyDirectories:
    """Tests for remove_empty_directories utility."""

    def test_single_empty_dir(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        empty = root / "empty"
        empty.mkdir()

        removed = remove_empty_directories(root)

        assert removed == 2  # empty dir + root itself
        assert not root.exists()

    def test_cascading_empty_dirs(self, tmp_path):
        root = tmp_path / "root"
        (root / "a" / "b" / "c").mkdir(parents=True)

        removed = remove_empty_directories(root)

        assert removed == 4  # c, b, a, root
        assert not root.exists()

    def test_preserves_files(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        (root / "empty").mkdir()
        (root / "has_file").mkdir()
        (root / "has_file" / "data.txt").write_text("content")

        removed = remove_empty_directories(root)

        assert removed == 1  # only "empty" removed
        assert root.exists()
        assert not (root / "empty").exists()
        assert (root / "has_file" / "data.txt").exists()

    def test_mixed_tree(self, tmp_path):
        root = tmp_path / "root"
        (root / "a" / "deep" / "empty").mkdir(parents=True)
        (root / "b").mkdir()
        (root / "b" / "keep.log").write_text("log")
        (root / "c" / "d").mkdir(parents=True)

        removed = remove_empty_directories(root)

        # a/deep/empty, a/deep, a, c/d, c = 5 empty dirs removed
        assert removed == 5
        assert root.exists()  # root has b/ with file
        assert (root / "b" / "keep.log").exists()

    def test_nonexistent_root(self, tmp_path):
        removed = remove_empty_directories(tmp_path / "nonexistent")
        assert removed == 0

    def test_file_as_root(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("x")
        removed = remove_empty_directories(f)
        assert removed == 0
        assert f.exists()

    def test_already_empty_root(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()

        removed = remove_empty_directories(root)

        assert removed == 1
        assert not root.exists()

    def test_nested_with_file_at_middle(self, tmp_path):
        root = tmp_path / "root"
        (root / "a" / "b" / "c").mkdir(parents=True)
        (root / "a" / "b" / "file.txt").write_text("data")

        removed = remove_empty_directories(root)

        # Only c is empty; a and b have content
        assert removed == 1
        assert (root / "a" / "b" / "file.txt").exists()
        assert not (root / "a" / "b" / "c").exists()
