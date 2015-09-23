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
"""See docstring for FileWaveImporter class"""
from autopkglib import Processor, ProcessorError
from distutils.version import LooseVersion, StrictVersion
import glob

import os
import os.path
import sys

# Ensure that the FWAdminClient can be imported from CommandLine module, since
# this Processor was imported via autopkg explicitly, the directory is not in
# the search path.
sys.path.append(os.path.dirname(__file__))

from CommandLine import FWAdminClient
from FWTool import COMMON_FILEWAVE_VARIABLES, FWTool

FW_FILESET_DESTINATION = "/Applications"
FILEWAVE_SUMMARY_RESULT = 'filewave_summary_result'

class FileWaveImporter(FWTool):
    """Imports a path as a fileset into FileWave.  The path points to either a Mac Package or a folder."""

    description = __doc__

    importer_variables = {
        "fw_import_source": {
            "required": True,
            "description": "The file/folder that will be imported into the FileWave fileset, can be dmg, pkg or folder.",
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
        },
        "fw_app_bundle_id": {
            "default": None,
            "required": False,
            "description": "If specified the importer will use this value to \
            locate other filesets representing the same application in order to \
            perform a version check - i.e. only newer app versions will be \
            imported.  This should be the CFBundleIdentifier from the apps Info.plist"
        },
        "fw_app_version": {
            "default": None,
            "required": False,
            "description": "This should be the CFBundleShortVersionString value \
                           from the apps Info.plist."
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


    def find_first_in_path(self, path, ext="app"):
        """Find app bundle at path."""
        #pylint: disable=no-self-use
        apps = glob.glob(os.path.join(path, "*.%s" % (ext)))
        if len(apps) == 0:
            raise ProcessorError("No %s found in dmg" % (ext))
        return apps[0]


    def main(self):
        self.validate_tools(print_path=False)

        fw_app_bundle_id = self.env.get('fw_app_bundle_id', None)
        fw_app_version = self.env.get('fw_app_version', None)
        check_version = fw_app_bundle_id is not None and fw_app_version is not None

        # perform version check by scanning existing filesets?
        if check_version:
            filesets = self.client.get_filesets()
            for fileset in filesets:
                app_bundle_id = fileset.custom_properties.get("autopkg_app_bundle_id", None)
                app_version = fileset.custom_properties.get("autopkg_app_version", None)

                if app_bundle_id == fw_app_bundle_id and \
                                LooseVersion(app_version) >= LooseVersion(fw_app_version):
                    print "This app version is already satisfied by the fileset %s called '%s' (%s, %s)" %\
                          (fileset.id, fileset.name, fw_app_bundle_id, fw_app_version )
                    return

        import_source = self.env['fw_import_source']
        if not os.path.exists(import_source):
            raise ProcessorError("Import source %s does not exist" %
                                 (import_source))

        fileset_name = self.env['fw_fileset_name']
        fileset_group = self.env.get('fw_fileset_group', None)
        destination_root = self.env.get('fw_destination_root',
                                        FW_FILESET_DESTINATION)
        find_type_in_dmg = self.env.get('fw_dmg_content_type', None)

        fileset_id = None
        dmg_mountpoint = None
        filename, file_extension = os.path.splitext(import_source)

        try:
            if file_extension in [ "dmg" ] and find_type_in_dmg is not None:
                dmg_mountpoint = self.mount(import_source)
                import_source = self.find_first_in_path(dmg_mountpoint, find_type_in_dmg)
                file_extension = find_type_in_dmg

            try:


                if file_extension in [ "pkg", "mpkg", "msi" ]:
                    fileset_id = self.client.import_package(path=import_source,
                                                       name=fileset_name,
                                                       root=destination_root,
                                                       target=fileset_group)
                elif os.path.isdir(import_source):
                    fileset_id = self.client.import_folder(path=import_source,
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

                if fileset_id is not None and check_version:
                    # re-write the props back into the fileset
                    self.client.set_property(fileset_id, "autopkg_app_bundle_id", fw_app_bundle_id)
                    self.client.set_property(fileset_id, "autopkg_app_version", fw_app_version)

            except Exception, e:
                raise ProcessorError("Error importing the folder '%s' into FileWave \
                                as a fileset called '%s', detail: %s" %
                                     (import_source, fileset_name, e))

        finally:
            if dmg_mountpoint is not None:
                self.unmount(dmg_mountpoint)

if __name__ == '__main__':
    PROCESSOR = FileWaveImporter()
    PROCESSOR.execute_shell()

