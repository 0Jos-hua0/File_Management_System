import os
import tempfile
import pytest
from core import file_ops

def test_create_and_delete_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "testfile.txt")
        file_ops.create_file(file_path)
        assert os.path.exists(file_path)
        file_ops.delete_file(file_path)
        assert not os.path.exists(file_path)

def test_rename_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src.txt")
        dst = os.path.join(tmpdir, "dst.txt")
        file_ops.create_file(src)
        file_ops.rename_file(src, dst)
        assert not os.path.exists(src)
        assert os.path.exists(dst)

def test_move_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src.txt")
        subdir = os.path.join(tmpdir, "subdir")
        os.mkdir(subdir)
        dst = os.path.join(subdir, "src.txt")
        file_ops.create_file(src)
        file_ops.move_file(src, dst)
        assert not os.path.exists(src)
        assert os.path.exists(dst)
