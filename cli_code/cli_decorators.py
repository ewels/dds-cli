###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import getpass
import logging
import pathlib
import sys
import json
import traceback
import functools
import dataclasses
import os
import inspect

# Installed
import botocore
import requests

# Own modules
from cli_code import user
from cli_code import base
from cli_code import file_handler as fh
from cli_code import s3_connector as s3
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

###############################################################################
# DECORATORS ##################################################### DECORATORS #
###############################################################################


def verify_proceed(func):
    """Decorator for verifying that the file is not cancelled.
    Also cancels the upload of all non-started files if break-on-fail."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception("Missing key word argument in wrapper over "
                            f"function {func.__name__}: 'file'")
        file = kwargs["file"]

        # Return if file cancelled by another file
        # log.debug("File: %s, Status: %s", file, self.status)
        if self.status[file]["cancel"]:
            message = f"File already cancelled, stopping upload " \
                f"of file {file}"
            log.warning(message)
            return False

        # Run function
        ok_to_proceed, message = func(self, *args, **kwargs)

        # Cancel file(s) if something failed
        if not ok_to_proceed:
            self.status[file].update({"cancel": True, "message": message})
            if self.break_on_fail:
                message = f"Cancelling upload due to file '{file}'. " \
                    "Break-on-fail specified in call."
                _ = [self.status[x].update({"cancel": True, "message": message})
                     for x in self.status if not self.status[x]["cancel"]
                     and not any([self.status[x]["put"]["started"],
                                  self.status[x]["put"]["done"]])
                     and x != file]

            log.debug("Status updated: %s", self.status[file])

        return ok_to_proceed

    return wrapped


def update_status(func):
    """Decorator for updating the status of files."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        # Check that function has correct args
        if "file" not in kwargs:
            raise Exception("Missing key word argument in wrapper over "
                            f"function {func.__name__}: 'file'")
        file = kwargs["file"]

        if func.__name__ not in ["put", "add_file_db"]:
            raise Exception(f"The function {func.__name__} cannot be used with"
                            " this decorator.")
        if func.__name__ not in self.status[file]:
            raise Exception(f"No status found for function {func.__name__}.")

        # Update status to started
        self.status[file][func.__name__].update({"started": True})

        # Run function
        ok_to_continue, message, *info = func(self, *args, **kwargs)

        if not ok_to_continue:
            return False, message

        # Update status to done
        self.status[file][func.__name__].update({"done": True})

        return ok_to_continue, message

    return wrapped


def verify_bucket_exist(func):
    """Check that s3 connection works, and that bucket exists."""

    @functools.wraps(func)
    def wrapped(self, *args, **kwargs):

        with s3.S3Connector(project_id=self.project, token=self.token) as conn:
            bucket_exists = conn.check_bucket_exists()
            if not bucket_exists:
                _ = conn.create_bucket()

        return func(self, conn, *args, **kwargs)

    return wrapped