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
import subprocess
from subprocess import CalledProcessError
import re
import json
import platform

__all__ = ["FileWaveFolderImporter"]

FW_FILESET_GROUP = "AutoPkg Import"
FW_FILESET_DESTINATION = "/Applications"

DEFAULT_FW_SERVER_HOST = "localhost"
DEFAULT_FW_SERVER_PORT = 20016

DEFAULT_FW_ADMIN_USERNAME = "fwadmin"
DEFAULT_FW_ADMIN_PASSWORD = "filewave"

class Client(object):
    def __init__(self, id, name, type, parent_id):
        self.id = str(id)
        self.name = name
        self.type = type
        self.parent_id = str(parent_id)

    def __str__(self):
        return "%s (%s) '%s', parent=%s" % (self.id, self.name, self.type, self.parent_id)


class Association(object):
    def __init__(self, assoc_id, client_id, fileset_id, kiosk=False, sw_update=False):
        self.id = str(assoc_id)
        self.client_id = str(client_id)
        self.fileset_id = str(fileset_id)
        self.kiosk = kiosk
        self.sw_update = sw_update

    def __str__(self):
        return "%s - Client: %s, Fileset: %s %s" % (
            self.id,
            self.client_id,
            self.fileset_id,
            "(Kiosk)" if self.kiosk else ""
        )


class Fileset(object):
    def __init__(self, id, name, type, size, parent_id):
        self.id = str(id)
        self.name = name
        self.type = type
        self.size = size
        self.parent_id = str(parent_id)

    def __str__(self):
        return "%s - name: %s, type: %s, parent: %s" % (
            self.id,
            self.name,
            self.type,
            self.parent_id,
        )

class FWAdminClient(object):
    def __init__(self,
                 admin_name = 'fwadmin',
                 admin_pwd = 'filewave',
                 server_host = 'localhost',
                 server_port = 20016,
                 create_fs_callback=None,
                 remove_fs_callback=None,
                 print_output=False):

        appPath = ''
        systemName = platform.system()

        if 'Darwin' == systemName:
            appPath = "%s/FileWave Admin.app/Contents/MacOS/FileWave Admin"
        elif 'Windows' == systemName:
            appPath = '%s/RelWithDebInfo/FileWaveAdmin.exe'
        elif 'Linux' == systemName:
            appPath = '%s/FileWaveAdmin'
        else:
            raise Exception( 'Unsupported platform' )

        self.fwadmin_executable = appPath % self.get_executable_path()
        self.connection_options = ['-u', admin_name,
                                   '-p', admin_pwd,
                                   '-H', server_host,
                                   '-P', server_port ]

        self.print_output = print_output
        self.create_fs_callback = create_fs_callback
        self.remove_fs_callback = remove_fs_callback

    @classmethod
    def get_executable_path(cls):
        return os.environ.get("FILEWAVE_ADMIN_PATH", '/Applications/FileWave')

    def run_admin(self, options, include_connection_options=True, error_expected=False, print_output=None):
        print_output = print_output or self.print_output
        process_options = [self.fwadmin_executable]
        if include_connection_options:
            process_options.extend(self.connection_options)
        if isinstance(options, basestring):
            process_options.append(options)
        else:
            process_options.extend(options)

        got_error = False
        ret = None
        try:
            if print_output:
                print process_options
            ret = subprocess.check_output(process_options, stderr=subprocess.STDOUT).rstrip()
        except CalledProcessError as e:
            got_error = True
            if print_output:
                print "Command failed, error code: ", e.returncode
                print "Ouput: ", e.output
            if not error_expected:
                raise e
            else:
                ret = e.output, e.returncode

        if error_expected and not got_error:
            raise Exception("Expected an error, but command was successful")

        return ret

    def get_clients(self):
        clients = json.loads(self.run_admin("--listClients"))

        def recursive_generator(client):
            children = client.pop('children', [])
            yield Client(**client)
            for child in children:
                for child_client in recursive_generator(child):
                    yield child_client

        for c in clients:
            for gg in recursive_generator(c):
                yield gg

    def get_filesets(self):
        filesets = json.loads(self.run_admin("--listFilesets"))

        def recursive_generator(fileset):
            children = fileset.pop('children', [])
            yield Fileset(**fileset)
            for child in children:
                for child_fileset in recursive_generator(child):
                    yield child_fileset

        for fs in filesets:
            for gg in recursive_generator(fs):
                yield gg

    def get_associations(self):
        associations = json.loads(self.run_admin(['--listAssociations']))

        for assoc in associations:
            yield Association(**assoc)

    def create_association(self, client_id, fileset_id, kiosk=False, sw_update=False, error_expected=False ):
        args = ['--createAssociation', '--clientgroup_id', client_id, '--fileset_id', fileset_id]
        if kiosk:
            args.append('--kiosk')

        if sw_update:
            args.append('--software_update')

        self.run_admin(args, error_expected=error_expected )

    def remove_association(self, assoc_id):
        self.run_admin(['--deleteAssociation', str(assoc_id)])

    def get_help(self):
        return self.run_admin("-h")

    def import_folder(self, path, name=None, root=None, target=None):
        options = ['--importFolder', path]
        if name:
            options.extend(["--name", name])
        if root:
            options.extend(["--root", root])
        if target:
            options.extend(["--target", str(target)])

        import_folder_result = self.run_admin(options)
        matcher = re.compile(r'new fileset with ID (?P<id>.+) was created')
        search = matcher.search(import_folder_result)
        id = search.group('id')
        if self.create_fs_callback and hasattr(self.create_fs_callback, '__call__'):
            self.create_fs_callback(id)
        return id

    def import_image(self, path, error_expected=False):
        options = ['--importImage', path]
        import_image_result = self.run_admin( options, error_expected=error_expected )
        matcher = re.compile( r'new imaging fileset with ID (?P<id>.+) was created')
        search = matcher.search(import_image_result)
        id = search.group('id')
        if self.create_fs_callback and hasattr(self.create_fs_callback, '__call__'):
            self.create_fs_callback(id)
        return id

    def import_package(self, path, name=None, root=None, target=None):
        options = ['--importPackage', path]
        if name:
            options.extend(["--name", name])
        if root:
            options.extend(["--root", root])
        if target:
            options.extend(["--target", str(target)])

        import_package_result = self.run_admin(options)
        matcher = re.compile(r'new fileset with ID (?P<id>.+) was created')
        search = matcher.search(import_package_result)
        id = search.group('id')
        if self.create_fs_callback and hasattr(self.create_fs_callback, '__call__'):
            self.create_fs_callback(id)
        return id

    def remove_fileset(self, fileset_id):
        self.run_admin(['--deleteFileset', str(fileset_id)])
        if self.remove_fs_callback and hasattr(self.remove_fs_callback, '__call__'):
            self.remove_fs_callback(fileset_id)
        return fileset_id

    def model_update(self):
        self.run_admin(['--updateModel'])

    def create_empty_fileset(self, name, target=None):
        options = ['--createFileset', str(name)]
        if target:
            options.extend(["--target", str(target)])
        create_empty_fileset_result = self.run_admin(options)
        print create_empty_fileset_result
        matcher = re.compile(r'new fileset (?P<id>.+) created with name (?P<name>.+)')
        search = matcher.search(create_empty_fileset_result)
        id = search.group('id')
        if self.create_fs_callback and hasattr(self.create_fs_callback, '__call__'):
            self.create_fs_callback(id)
        return id

FILEWAVE_SUMMARY_RESULT = 'filewave_summary_result'

class FileWaveProcessor(Processor):
    pass

class FileWaveFolderImporter(FileWaveProcessor):
    """Imports a directory as a fileset into FileWave."""

    description = __doc__

    input_variables = {
        "FW_SERVER_HOST": {
            "description": ("The hostname/ip of the FileWave server.  Defaults to %s"
                           % DEFAULT_FW_SERVER_HOST),
            "required": True,
        },
        "FW_SERVER_PORT": {
            "description": ("The port number of the FileWave server.  Defaults to %s"
                            % DEFAULT_FW_SERVER_PORT),
            "required": True,
        },
        "FW_ADMIN_USER": {
            "description": ("The username to use when connecting to the FileWave server.  Defaults to %s"
                            % DEFAULT_FW_ADMIN_USERNAME),
            "required": True,
        },
        "FW_ADMIN_PASSWORD": {
            "description": ("The password to use when connecting to the FileWave server.  Defaults to %s"
                            % DEFAULT_FW_ADMIN_PASSWORD),
            "required": True,
        },
        "import_source": {
            "required": True,
            "description": "The file/folder that will be imported into the FileWave fileset, can be pkg or folder.",
        },
        "fileset_name": {
            "required": True,
            "description": "The name of the fileset to be created (will be made unique if it isnt already).",
        },
        "fileset_group": {
            "required": False,
            "description": "The name of the fileset group to import into - can be left blank, will be created if it does not exist.",
        },
        "destination_root": {
            "required": False,
            "description": ("The location at which to place all the imported data.  Defaults to %s"
                             % FW_FILESET_DESTINATION ),
        },
    }

    output_variables = {
        "fileset_id": {
            "description": "The resulting FileWave fileset ID for the newly created fileset."
        },
        FILEWAVE_SUMMARY_RESULT: {
            "description": "Summary of what was imported into FileWave."
        }}

    def main(self):
        client = FWAdminClient(
            admin_name=self.env.get('FW_ADMIN_USER', DEFAULT_FW_ADMIN_USERNAME),
            admin_pwd=self.env.get('FW_ADMIN_PASSWORD', DEFAULT_FW_ADMIN_PASSWORD),
            server_host=self.env.get('FW_SERVER_HOST', DEFAULT_FW_SERVER_HOST),
            server_port=self.env.get('FW_SERVER_PORT', DEFAULT_FW_SERVER_PORT),
            print_output=True
        )

        import_source = self.env['import_source']

        fileset_name = self.env['fileset_name']
        fileset_group = self.env.get('fileset_group', None)
        destination_root = self.env.get('destination_root', FW_FILESET_DESTINATION)

        try:
            # TODO: if input_source is pkg use import_package not import_folder

            self.env['fileset_id'] = client.import_folder(path=import_source,
                                                          name=fileset_name,
                                                          root=destination_root,
                                                          target=fileset_group)

            if FILEWAVE_SUMMARY_RESULT in self.env:
                del self.env[FILEWAVE_SUMMARY_RESULT]

            self.env[FILEWAVE_SUMMARY_RESULT] = {
                'summary_text': 'The following fileset was imported:',
                'report_fields': ['fileset_id', 'Fileset Group', 'Fileset Name'],
                'data': {
                    'fileset_id': self.env['fileset_id'],
                    'fileset_group': fileset_group,
                    'fileset_name': fileset_name
                }
        }
        except Exception, e:
            raise ProcessorError("Error importing the folder '%s' into FileWave as a fileset called '%s', detail: %s" %
                                 (import_source, fileset_name, e))

        self.output("Created Fileset <%s> from folder '%s' at root '%s'"
                    % (fileset_name, import_source, destination_root))

if __name__ == '__main__':
    PROCESSOR = FileWaveFolderImporter()
    PROCESSOR.execute_shell()

