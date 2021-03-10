"""User module."""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library
import logging
import sys
import dataclasses
import os
import requests

# Installed
import rich

# Own modules
from cli_code import DDSEndpoint

###############################################################################
# START LOGGING CONFIG ################################# START LOGGING CONFIG #
###############################################################################

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

###############################################################################
# CLASSES ########################################################### CLASSES #
###############################################################################


@dataclasses.dataclass
class User:
    """Authenticates the DDS user."""

    username: str = None
    password: dataclasses.InitVar[str] = None
    project: dataclasses.InitVar[str] = None
    token: dict = dataclasses.field(init=False)

    def __post_init__(self, password, project):
        # Username and password required for user authentication
        if None in [self.username, password]:
            sys.exit("Missing user information.")

        # Authenticate user and get delivery JWT token
        self.token = self.__authenticate_user(password=password, project=project)

    # Private methods ######################### Private methods #
    def __authenticate_user(self, password, project):
        """Authenticates the username and password via a call to the API."""

        LOG.debug(project)
        # Project passed in to add it to the token. Can be None.
        response = requests.get(
            DDSEndpoint.AUTH,
            params={"project": project},
            auth=(self.username, password),
        )

        if not response.ok:
            console = rich.console.Console()
            console.print(f"{response.text}")
            os._exit(1)

        token = response.json()
        LOG.debug(token)
        return {"x-access-token": token["token"]}

    # Public methods ########################### Public methods #
