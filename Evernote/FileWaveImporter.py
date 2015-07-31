#!/usr/bin/python
#
# Copyright 2015 FileWave (Europe) GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for DmgCreator class"""
from autopkglib import Processor, ProcessorError

import os
import os.path
import sys

# Ensure that the FWAdminClient can be imported from CommandLine module, since
# this Processor was imported via autopkg explicitly, the directory is not in
# the search path.
sys.path.append(os.path.dirname(__file__))

from CommandLine import FWAdminClient

__all__ = ["FileWaveImporter"]

FW_FILESET_DESTINATION = "/Applications"

DEFAULT_FW_SERVER_HOST = "localhost"
DEFAULT_FW_SERVER_PORT = "20016"
DEFAULT_FW_ADMIN_USERNAME = "fwadmin"
DEFAULT_FW_ADMIN_PASSWORD = "filewave"

FILEWAVE_SUMMARY_RESULT = 'filewave_summary_result'

COMMON_FILEWAVE_VARIABLES = {
        "FW_SERVER_HOST": {
            "default": DEFAULT_FW_SERVER_HOST,
            "description": ("The hostname/ip of the FileWave server.  Defaults to %s"
                           % DEFAULT_FW_SERVER_HOST),
            "required": False,
        },
        "FW_SERVER_PORT": {
            "default": DEFAULT_FW_SERVER_PORT,
            "description": ("The port number of the FileWave server.  Defaults to %s"
                            % DEFAULT_FW_SERVER_PORT),
            "required": False,
        },
        "FW_ADMIN_USER": {
            "default": DEFAULT_FW_ADMIN_USERNAME,
            "description": ("The username to use when connecting to the FileWave server.  Defaults to %s"
                            % DEFAULT_FW_ADMIN_USERNAME),
            "required": False,
        },
        "FW_ADMIN_PASSWORD": {
            "default": DEFAULT_FW_ADMIN_PASSWORD,
            "description": ("The password to use when connecting to the FileWave server.  Defaults to %s"
                            % DEFAULT_FW_ADMIN_PASSWORD),
            "required": False,
        }
}

class FileWaveImporter(Processor):
    """Imports a path as a fileset into FileWave.  The path points to either a Mac Package or a folder."""

    description = __doc__

    importer_variables = {
        "fw_import_source": {
            "required": True,
            "description": "The file/folder that will be imported into the FileWave fileset, can be pkg or folder.",
        },
        "fw_fileset_name": {
            "required": True,
            "description": "The name of the fileset to be created (will be made unique if it isnt already).",
        },
        "fw_fileset_group": {
            "required": False,
            "description": "The name of the fileset group to import into - can be left blank, will be created if it does not exist.",
        },
        "fw_destination_root": {
            "default": FW_FILESET_DESTINATION,
            "required": False,
            "description": ("The location at which to place all the imported data.  Defaults to %s"
                             % FW_FILESET_DESTINATION )
        }
    }

    input_variables = dict(COMMON_FILEWAVE_VARIABLES, **importer_variables)

    output_variables = {
        "fw_fileset_id": {
            "description": "The resulting FileWave fileset ID for the newly created fileset."
        },
        FILEWAVE_SUMMARY_RESULT: {
            "description": "Summary of what was imported into FileWave."
        }}

    def main(self):
        client = FWAdminClient(
            admin_name=self.env['FW_ADMIN_USER'],
            admin_pwd=self.env['FW_ADMIN_PASSWORD'],
            server_host=self.env['FW_SERVER_HOST'],
            server_port=self.env['FW_SERVER_PORT'],
            print_output=True
        )

        app_version = self.env.get('version', None)
        if app_version is not None:
            # get all filesets and see if we have an app with this name, at
            # a lower version - if not, we can import.
            filesets = client.get_filesets()
            for fileset in filesets:
                print fileset
            pass

        import_source = self.env['fw_import_source']
        if not os.path.exists(import_source):
            raise ProcessorError("Import source %s does not exist" %
                                 (import_source))

        fileset_name = self.env['fw_fileset_name']
        fileset_group = self.env.get('fw_fileset_group', None)
        destination_root = self.env.get('fw_destination_root',
                                        FW_FILESET_DESTINATION)
        fileset_id = None

        try:

            filename, file_extension = os.path.splitext(import_source)
            if file_extension in [ "pkg", "mpkg", "msi" ]:
                fileset_id = client.import_package(path=import_source,
                                                   name=fileset_name,
                                                   root=destination_root,
                                                   target=fileset_group)
            elif os.path.isdir(import_source):
                fileset_id = client.import_folder(path=import_source,
                                                  name=fileset_name,
                                                  root=destination_root,
                                                  target=fileset_group)

            if FILEWAVE_SUMMARY_RESULT in self.env:
                del self.env[FILEWAVE_SUMMARY_RESULT]

            self.env[FILEWAVE_SUMMARY_RESULT] = {
                'summary_text': 'The following fileset was imported:',
                'report_fields': ['fw_fileset_id', 'fw_fileset_group', 'fw_fileset_name'],
                'data': {
                    'fw_fileset_id': fileset_id,
                    'fw_fileset_group': fileset_group if not None else "Root",
                    'fw_fileset_name': fileset_name
                }}

            self.env['fw_fileset_id'] = fileset_id

        except Exception, e:
            raise ProcessorError("Error importing the folder '%s' into FileWave \
                            as a fileset called '%s', detail: %s" %
                                 (import_source, fileset_name, e))

        self.output("Created Fileset <%s> from folder '%s' at root '%s'"
                    % (fileset_name, import_source, destination_root))

if __name__ == '__main__':
    PROCESSOR = FileWaveImporter()
    PROCESSOR.execute_shell()

