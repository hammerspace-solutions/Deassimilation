#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2025 Hammerspace, Inc
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# -----------------------------------------------------------------------------
# DirectoryWalker.py
#
# Class that will handle walking through a directory. Each time it hits a new
# directory that HAS files in it, it will spin off a process to handle the files
# in that directory.

import multiprocessing as mp
import os
import sys
import signal
import json
import queue
import time
import logging
import traceback
import humanize
from pathlib import Path
from typing import Any, Optional, List, Dict, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from deassimilateUtils.Logger import Logger

import dill  # For better function serialization

# Define the name of the Program, Description, and Version

progname = "DirectoryWalker"
progdesc = "Walk directories in parallel"
progvers = "1.0.0"

# Install if needed: pip install dill

@dataclass
class FileResult:
    filepath: Path
    status: str
    result: Any
    error: Optional[str] = None


@dataclass
class DirectoryResult:
    directory: Path
    status: str
    file_results: List[FileResult]
    processing_result: Optional[Dict] = None  # Changed from 'result' to avoid conflict
    error: Optional[str] = None

class ResultProcessor(ABC):
    @abstractmethod
    def process_directory_result(self, result: DirectoryResult) -> None:
        pass

    @abstractmethod
    def process_file_result(self, result: FileResult) -> None:
        pass


class VarFormatter(logging.Formatter):
    default_formatter = logging.Formatter("%(levelname)s: %(message)s")

    def __init__(self, formats):
        """ formats is a dict { loglevel : logformat } """
        self.formatters = {}
        for loglevel in formats:
            self.formatters[loglevel] = logging.Formatter(formats[loglevel])

    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.default_formatter)
        return formatter.format(record)


class DefaultResultProcessor(ResultProcessor):
    def process_directory_result(self, result: DirectoryResult) -> None:
        if result.status == "success":
            self.total_directories += 1

            # Update file count and size

            self.total_files += result.processing_result.get('total_files', 0)
            self.total_size += result.processing_result.get('total_size_bytes', 0)
            
    def process_file_result(self, result: FileResult) -> None:
        pass

    def __init__(self, logger: Logger = None):
        self.total_directories = 0
        self.total_files = 0
        self.total_size = 0
        
        self.logger = logger

# Function that will only get filenames from a given directory
#
# We need this function because passing the filenames on the queue
# proved that we can overrun the queue with large directories

def _get_files_only(dirpath, logger=None):
    """Get only files and symlinks to files (no directories)"""

    filenames = []
    
    with os.scandir(dirpath) as entries:
        for entry in entries:
            if entry.is_file(follow_symlinks=False):
                filenames.append(entry.name)
            elif entry.is_symlink():
                # Check if symlink points to a file
                try:
                    target = os.path.realpath(entry.path)
                    if os.path.isfile(target):
                        filenames.append(entry.name)
                except (OSError, RuntimeError) as e:
                    # Broken symlink or permission error
                    if logger is not None:
                        logger.debug(f"Broken symlink or permission: {e}")
                    continue

    if logger is not None:
        logger.debug(f"Found {len(filenames)} files")

    return filenames

# Worker process that handles directories from the queue

def _worker_function(task_queue: mp.Queue,
                     result_queue: mp.Queue,
                     processor_func_serialized: bytes,
                     need_logger: bool,
                     **kwargs):

    # Setup a logger so that we can track any errors

    if need_logger:
        pid = os.getpid()
        log_filename = f"{progname}-{pid}.log"
        log_level = logging.DEBUG
        logger = Logger(name=progname,
                        version=progvers,
                        description=progdesc,
                        level=log_level,
                        pathname=log_filename)
    else:
        logger = None
    
    # Handle a SIGTERM... We will only get this if we are too busy to take
    # our poison pill

    def handle_sigterm(signum, frame):
        if logger is not None:
            logger.error("Worker received SIGTERM. Shutting down immediately!")
        else:
            print("Worker received SIGTERM. Shutting down immediately!")
        raise SystemExit(1)

    # Setup to handle the SIGTERM signal

    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Deserialize the processor function once when worker starts

    processor_func = dill.loads(processor_func_serialized)

    # Loop and get items off the queue... If None on queue, then terminate gracefully
    
    while True:
        try:
            if logger is not None:
                logger.debug("Waiting to take item off queue")

            # Wait to get a unit of work from the master process
            
            task = task_queue.get(timeout=1)
            if task is None:  # Poison pill
                if logger is not None:
                    logger.debug("Poison pill received")
                break

            directory, filenames = task
            if logger is not None:
                logger.debug(f"queue: {directory}")

            # Now we have to get the filenames from the directory. This used to be
            # passed in via the queue, but the queue became overloaded on large
            # directories. So, we get those entries here instead.

            filenames = _get_files_only(directory, logger)

            # Process the directory and files
            
            try:
                # Convert filenames to Path objects
                file_paths = [directory / filename for filename in filenames]

                # Call the processor function
                processing_result = processor_func(directory,
                                                   filenames,
                                                   logger,
                                                   **kwargs)

                # More debugging for file results

                if logger is not None:
                    logger.debug(f"Result: {json.dumps(processing_result, indent=4)}")

                # Create FileResult objects for each file

                file_results = [
                    FileResult(
                        filepath=file_path,
                        status="success",
                        result=None
                    ) for file_path in file_paths
                ]
                
                dir_result = DirectoryResult(
                    directory=directory,
                    status="success",
                    file_results=file_results,
                    processing_result=processing_result,
                    error=None
                )
            except Exception as e:
                dir_result = DirectoryResult(
                    directory=directory,
                    status="error",
                    file_results=[],
                    processing_result=None,
                    error=str(e)
                )
            
            result_queue.put(dir_result)
        except queue.Empty:
            continue
        except Exception as e:
            if logger is not None:
                logger.debug(f"Received queue error: {e}")
            result_queue.put(DirectoryResult(
                directory=Path("unknown"),
                status="error",
                file_results=[],
                processing_result=None,
                error=str(e)
            ))

class DirectoryWalker:
    def __init__(
        self,
        processor_func: Callable[[Path, List[Path], ...], Any],
        max_processes: int = 50,
        name: str = progname,
        description: str = progdesc,
        version: str = progvers,
        logger: Logger = None,
        result_processor: Optional[ResultProcessor] = None,
        **kwargs    
    ):
        self.max_processes = max_processes
        self.name = name
        self.logger = logger
        
        # Only create a logger if they didn't pass one in...

        if self.logger is None:
            self.logger = Logger(name=name,
                                 version=version,
                                 description=description,
                                 level=logging.DEBUG)

        # Setup a results processor

        self.result_processor = result_processor if result_processor is not None \
            else DefaultResultProcessor(process_results=False, logger=logger)
        self.kwargs = kwargs
        
        # Serialize the processor function once during initialization

        self.processor_func_serialized = dill.dumps(processor_func)
        
        # Create queues

        self.manager = mp.Manager()
        self.task_queue = self.manager.Queue()
        self.result_queue = self.manager.Queue()

    def _results_handler(self):
        """Handles results from worker processes"""
        while True:
            try:
                result = self.result_queue.get(timeout=1)

                self.logger.debug("Got item from results queue")
                
                # Skip processing if result_processor is None
                if self.result_processor is not None:
                    self.result_processor.process_directory_result(result)
                
                    # Process individual file results
                    for file_result in result.file_results:
                        self.result_processor.process_file_result(file_result)

            except queue.Empty:
                if not any(p.is_alive() for p in self.workers):
                    self.logger.debug("Results queue is empty and workers dead")
                    break
            except Exception as e:
                self.logger.error(f"Error processing result: {str(e)}")

    def walk_directories(self, root_path: Path):
        """
        Walk through directories incrementally without pre-collecting all paths
        """
        self.logger.info(f"Starting directory walk from {root_path}")

        # Determine if the worker will have a logger or not. This is really
        # only needed when debugging...

        cur_log_level = self.logger.level
        if cur_log_level == logging.DEBUG:
            need_logger = True
        else:
            need_logger = False
            
        # Start worker processes

        self.logger.debug(f"Creating {self.max_processes} multiprocessing structures")
        self.workers = [
            mp.Process(
                target=_worker_function,
                args=(self.task_queue,
                      self.result_queue,
                      self.processor_func_serialized,
                      need_logger),
                kwargs=self.kwargs
            )
            for _ in range(self.max_processes)
        ]

        self.logger.debug(f"Starting {self.max_processes} processes")
        for w in self.workers:
            w.start()
        
        # Start results handler in a separate thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            results_future = executor.submit(self._results_handler)
            
            try:
                # Walk directories and feed them to workers incrementally
                for dirpath, dirnames, filenames in os.walk(root_path):
                    self.logger.debug(f"Putting work on queue for dir: {dirpath}")
                    self.task_queue.put((Path(dirpath), []))

                    # We need to do the following because our workers might
                    # have died...

                    if not any(p.is_alive() for p in self.workers):
                        self.logger.error("All the workers are dead!")

                        for p in self.workers:
                            p.join()

                        self.logger.error("Workers are cleaned up. Aborting!")
                        return
                        
                # Signal workers to exit when done
                for _ in self.workers:
                    self.task_queue.put(None)
                
                # Wait for workers to finish
                self.logger.debug("Waiting for worker processes to finish")
                for w in self.workers:
                    w.join()
                self.logger.debug("Work processes are finished")
                
                # Wait for results handler to complete
                results_future.result()

            # Keyboard interrupt caught. Terminate gracefully

            except KeyboardInterrupt:
                self.logger.info("\nCtrl-C detected! Shutting down workers...")

                # Send poison pills to workers

                for _ in self.workers:
                    self.task_queue.put(None)

                # Wait a moment for workers to finish

                time.sleep(5)

                # Force terminate if they're still running

                for w in self.workers:
                    if w.is_alive():
                        w.terminate()

                # Cancel the results handler

                results_future.cancel()
                raise
            
            # Unknown exception, terminate
            
            except Exception as e:
                self.logger.error(f"Error in main processing loop: {str(e)}")
                self.logger.debug(traceback.format_exc())
                
                # Clean up
                for w in self.workers:
                    if w.is_alive():
                        w.terminate()
                results_future.cancel()

# Example processor function (can be defined anywhere)

def process_directory_content(directory: Path,
                              file_names: List,
                              logger = None,
                              **kwargs) -> Dict:
        
    extension_counts = {}
    total_size = 0

    if logger is not None:
        logger.debug(f"Going through path: {directory}")
        
    for file_name in file_names:
        file_path = directory / file_name
        ext = file_path.suffix.lower()
        extension_counts[ext] = extension_counts.get(ext, 0) + 1
        total_size += file_path.stat().st_size
    
    return {
        "directory": str(directory),
        "total_files": len(file_names),
        "extension_counts": extension_counts,
        "total_size_bytes": total_size
    }

# Custom result processor
class CustomResultProcessor(ResultProcessor):
    def __init__(self,
                 logger: Logger = None):
        self.total_directories = 0
        self.total_files = 0
        self.total_size = 0

        self.logger = logger
        
    def process_directory_result(self, result: DirectoryResult):
        if result.status == "success":
            self.total_directories += 1
            if self.logger is not None:
                self.logger.info(f"\nDirectory: {result.directory}")
            else:
                print(f"\nProcessed directory: {result.directory}")
            
            # Update file count and size from processing_result

            self.total_files += result.processing_result.get('total_files', 0)
            self.total_size += result.processing_result.get('total_size_bytes', 0)
            if self.logger is not None:
                self.logger.info(f"Results: {result.processing_result}")
            else:
                print(f"Results: {result.processing_result}")
        else:
            if self.logger is not None:
                self.logger.error(f"\nError processing directory {result.directory}: {result.error}")
            else:
                print(f"\nError processing directory {result.directory}: {result.error}")

    def process_file_result(self, result: FileResult):
        if result.status == "success":
            pass  # File counts are now handled via processing_result

if __name__ == '__main__':
    # Set up logging

    logger = None
#    logger = Logger(name=progname,
#                    version=progvers,
#                    description=progdesc,
#                    level=logging.INFO)

    # Create result processor

    result_processor = CustomResultProcessor()

    # Create walker instance with the processor function

    walker = DirectoryWalker(
        processor_func=process_directory_content,
        max_processes=1,
        name=progname,
        description=progdesc,
        version=progvers,# Using more processes for better demonstration
        logger=logger,
        result_processor=result_processor
    )

    # Process directories

    root_path = Path("/Users/mike.kade/PycharmProjects")

    # Walk the directories through parallel processing

    try:
        walker.walk_directories(root_path)
    except KeyboardInterrupt:
        print(f"Caught ctrl-C in main code. Terminating with no other processing.")
        sys.exit(1)

    # Print summary

    if result_processor is not None:
        print("\nProcessing Summary:")
        print(f"Processed directories: {result_processor.total_directories}")
        print(f"Processed files: {result_processor.total_files}")
        print(f"Total size: {humanize.naturalsize(result_processor.total_size)}")
