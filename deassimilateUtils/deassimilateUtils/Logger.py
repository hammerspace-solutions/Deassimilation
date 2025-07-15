#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2024 Hammerspace, Inc
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
# Logger.py
#
# Logger class... Provides global logger access and handles initiation

# import libs

import os
import logging
from typing import Union

# Define the name of the Program, Description and Version

progname = "Logger"
progdesc = "Custom class to handle all logging"
progvers = "1.0.0"

# This is a minor override of the logging class. The main thing that we do is set a formatter
# and output a warning if they set debugging mode

class Logger(logging.Logger):
    '''
    Provides a Logger object
    '''

    def __init__(self,
                 name: str=progname,
                 version: str=progvers,
                 description: str=progdesc,
                 level: Union[str, int]=None,
                 pathname: str=None):
        '''
        Constructor

        :param name: Program name
        :param version: Version of the program
        :param description: Description of the program
        :param level: Log level (INFO, WARNING, ERROR, DEBUG)
        '''

        self.name = name
        self.version = version
        self.description = description

        # Instantiate the logger

        super(Logger, self).__init__(self.name)

        # If they have already instantiated this logger previously, we will know if
        # there are handlers  already connected.

        info_format = "%(message)s"

        # Build formatter

        formatter = VarFormatter({logging.INFO: f"{info_format}",
                                  logging.WARNING: '%(levelname)s: %(message)s',
                                  logging.ERROR: '%(levelname)s: %(asctime)s %(message)s',
                                  logging.DEBUG: '%(levelname)s: %(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s'})

        # Destroy any old handlers

        if self.hasHandlers():

            for handler in self.handlers:
                self.removeHandler(handler)
                handler.close()

        # Set the default level

        self.setLevel(level)

        # Configure handlers
        # Console

        self.console = logging.StreamHandler()
        self.console.setLevel(level)
        self.console.setFormatter(formatter)
        self.addHandler(self.console)

        # If they included a pathname, then also open a logger to a file...

        if pathname is not None:
            file_handler = logging.FileHandler(pathname, mode="a")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            self.addHandler(file_handler)

        # Output a "Logger initialized" message

        new_level = logging.getLevelName(self.level).upper()
        self.debug("Logger Initialized")
        self.debug(f"Level - '{new_level}'")

        if description is not None:
            self.info(f"{self.name} - {self.version} - {self.description}")
        else:
            self.info(f"{self.name} - {self.version}")

    # Change the level of the logger

    def setLevel(self, level: Union[str, int]):

        super(Logger, self).setLevel(level)

        # If there are handlers, we have to change them too

        for handler in self.handlers:
            handler.setLevel(self.level)

        # Issue a warning if the level becomes DEBUG

        new_level = logging.getLevelName(self.level).upper()
        if new_level == "DEBUG":
            self.warning(f"Debug level set to '{new_level}'. This may hinder performance")


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


def main():

    # Build a pathname for the logger...

    pid = os.getpid()
    log_pathname = f"{progname}_{pid}.log"

    logger = Logger(name=progname, version=progvers, level="DEBUG", pathname=log_pathname)

    logger.info("This is an info message")
    logger.error("This is an error message")
    logger.warning("This is a warning message")
    logger.debug("This is a debug message")

    logger.setLevel("INFO")
    logger.error("Changed to INFO")
    logger.info("This is an info message")
    logger.error("This is an error message")
    logger.warning("This is a warning message")
    logger.debug("This is a debug message")

    logger.setLevel("WARNING")
    logger.error("Changed to WARNING")
    logger.info("This is an info message")
    logger.error("This is an error message")
    logger.warning("This is a warning message")
    logger.debug("This is a debug message")

    logger.setLevel("DEBUG")
    logger.error("Changed to DEBUG")
    logger.info("This is an info message")
    logger.error("This is an error message")
    logger.warning("This is a warning message")
    logger.debug("This is a debug message")

    # Can we intercept other libraries logs?

    lib_logger = logging.getLogger("some_library")
    lib_logger.setLevel(logging.DEBUG)
#    lib_logger.addHandler()
    lib_logger.propogate = False
    pass

if __name__ == "__main__":
    main()
