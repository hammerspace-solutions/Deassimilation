import pytest
import os
import tempfile
import shutil

@pytest.fixture
def temp_directory():
    """Create a temporary directory structure for testing"""
    temp_dir = tempfile.mkdtemp()
    
    # Create a basic directory structure
    os.makedirs(os.path.join(temp_dir, "dir1/subdir1"))
    os.makedirs(os.path.join(temp_dir, "dir2/subdir2"))
    
    # Create some files
    with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
        f.write("test1")
    with open(os.path.join(temp_dir, "dir1/file2.txt"), "w") as f:
        f.write("test2")
    with open(os.path.join(temp_dir, "dir1/subdir1/file3.txt"), "w") as f:
        f.write("test3")
    
    # Create a symlink
    os.symlink(
        os.path.join(temp_dir, "file1.txt"),
        os.path.join(temp_dir, "link1.txt")
    )
    
    # Create a FIFO file
    fifo_path = os.path.join(temp_dir, "fifo1")
    os.mkfifo(fifo_path)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)
