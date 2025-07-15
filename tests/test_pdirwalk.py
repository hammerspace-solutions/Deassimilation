import pytest
import os
import tempfile
import shutil
from deassimilateUtils.pdirwalk import pdirwalk, ResultsProcessor, get_filetype
import stat

class TestResultsProcessor(ResultsProcessor):
    def _setup(self):
        self.results = []
    
    def _process(self, res):
        self.results.append(res)
    
    def _get_results(self):
        return self.results

def test_basic_directory_walk(temp_directory):
    """Test basic directory walking functionality"""
    files_found = []
    
    def process_dir(proc_id, static_args, work_id, dir_path, filenames):
        files_found.extend([os.path.join(dir_path, f) for f in filenames])
        return work_id
    
    pdirwalk(temp_directory, process_dir, numjobs=2)
    
    assert len(files_found) == 3  # file1.txt, file2.txt, file3.txt
    assert any("file1.txt" in f for f in files_found)
    assert any("file2.txt" in f for f in files_found)
    assert any("file3.txt" in f for f in files_found)

def test_results_processor(temp_directory):
    """Test the ResultsProcessor functionality"""
    def process_dir(proc_id, static_args, work_id, dir_path, filenames):
        static_args.q.put((proc_id, dir_path, filenames))
        return work_id
    
    results_processor = TestResultsProcessor()
    pdirwalk(temp_directory, process_dir, numjobs=2, results_processor=results_processor)
    
    # Check that results were collected
    assert len(results_processor.final_results) > 0
    
    # Verify that all directories were processed
    processed_dirs = set(result[1] for result in results_processor.final_results)
    expected_dirs = {
        temp_directory,
        os.path.join(temp_directory, "dir1"),
        os.path.join(temp_directory, "dir1/subdir1"),
        os.path.join(temp_directory, "dir2"),
        os.path.join(temp_directory, "dir2/subdir2")
    }
    assert processed_dirs.issuperset(expected_dirs)

def test_file_types(temp_directory):
    """Test different file type detection"""
    file_types = {}
    
    def process_dir(proc_id, static_args, work_id, dir_path, filenames):
        for filename in filenames:
            full_path = os.path.join(dir_path, filename)
            file_types[full_path] = get_filetype(os.stat(full_path))
        return work_id
    
    pdirwalk(temp_directory, process_dir, numjobs=2)
    
    # Check regular files
    assert any(ft == "REGULAR" for ft in file_types.values())
    
    # Check symlink
    link_path = os.path.join(temp_directory, "link1.txt")
    assert file_types[link_path] == "SYMLINK"
    
    # Check FIFO
    fifo_path = os.path.join(temp_directory, "fifo1")
    assert file_types[fifo_path] == "FIFO"

def test_error_handling(temp_directory):
    """Test error handling for inaccessible directories"""
    restricted_dir = os.path.join(temp_directory, "restricted")
    os.makedirs(restricted_dir)
    os.chmod(restricted_dir, 0o000)  # Remove all permissions
    
    def process_dir(proc_id, static_args, work_id, dir_path, filenames):
        return work_id
    
    # Should not raise an exception, but log an error
    pdirwalk(temp_directory, process_dir, numjobs=2)
    
    # Cleanup
    os.chmod(restricted_dir, 0o755)

def test_concurrent_processing(temp_directory):
    """Test that multiple jobs are actually running concurrently"""
    import time
    
    processed_times = []
    
    def slow_process_dir(proc_id, static_args, work_id, dir_path, filenames):
        time.sleep(0.1)  # Simulate some work
        processed_times.append(time.time())
        return work_id
    
    start_time = time.time()
    pdirwalk(temp_directory, slow_process_dir, numjobs=4)
    end_time = time.time()
    
    # If processing is concurrent, total time should be less than
    # (number of directories * 0.1 seconds)
    total_dirs = len([d for d, _, _ in os.walk(temp_directory)])
    assert end_time - start_time < (total_dirs * 0.1)

if __name__ == "__main__":
    pytest.main([__file__])
