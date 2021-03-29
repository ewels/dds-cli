"""Remote file handler module"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import os
import pathlib

# Installed
import requests
import rich

# Own modules
from cli_code import DDSEndpoint
from cli_code import file_handler as fh

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# RICH CONFIG ################################################### RICH CONFIG #
###############################################################################

console = rich.console.Console()

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


class RemoteFileHandler(fh.FileHandler):
    """Collects the files specified by the user."""

    # Magic methods ################ Magic methods #
    def __init__(self, get_all, user_input, token, destination=pathlib.Path("")):

        # Initiate FileHandler from inheritance
        super().__init__(user_input=user_input, local_destination=destination)

        self.get_all = get_all

        self.data_list = list(set(self.data_list))

        if not self.data_list and not get_all:
            console.print("\n:warning: No data specified. :warning:\n")
            os._exit(os.EX_OK)

        self.data = self.__collect_file_info_remote(
            all_paths=self.data_list, token=token
        )
        self.data_list = None

    def __collect_file_info_remote(self, all_paths, token):
        """Get information on files in db."""

        # Get file info from db via API
        try:
            response = requests.get(
                DDSEndpoint.FILE_INFO_ALL if self.get_all else DDSEndpoint.FILE_INFO,
                headers=token,
                json=all_paths,
            )
        except requests.ConnectionError as err:
            LOG.fatal(err)
            os._exit(os.EX_OK)

        # Server error or error in response
        if not response.ok:
            console.print(f"\n{response.text}\n")
            os._exit(os.EX_OK)

        # Get file info from response
        file_info = response.json()

        # Folder info required if specific files requested
        if all_paths and "folders" not in file_info:
            console.print(
                "\n:warning: Error in response. "
                "Not enough info returned despite ok request. :warning:\n"
            )
            os._exit(os.EX_OK)

        # Files in response always required
        if "files" not in file_info:
            console.print(
                "\n:warning: No files in response despite ok request. :warning:\n"
            )
            os._exit(os.EX_OK)

        # files and files in folders from db
        files = file_info["files"]
        folders = file_info["folders"] if "folders" in file_info else {}

        # Cancel download of those files or folders not found in the db
        self.failed = {
            x: {"error": "Not found in DB."}
            for x in all_paths
            if x not in files and x not in folders
        }

        # Save info on files in dict and return
        data = {
            self.destination / pathlib.Path(x): {**y, "name_in_db": x}
            for x, y in files.items()
        }

        # Save info on files in a specific folder and return
        for x, y in folders.items():
            data.update(
                {
                    self.destination
                    / pathlib.Path(z[0]): {
                        "name_in_db": z[0],
                        "name_in_bucket": z[1],
                        "subpath": z[2],
                        "size": z[3],
                    }
                    for z in y
                }
            )

        return data

    def create_download_status_dict(self):
        """Create dict for tracking file download status."""

        status_dict = {}
        for x in list(self.data):
            status_dict[x] = {
                "cancel": False,
                "message": "",
                "get": {"started": False, "done": False},
                "update_db": {"started": False, "done": False},
            }

        return status_dict