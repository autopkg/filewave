import subprocess
from subprocess import CalledProcessError
import re, os
import json
import platform
import os.path

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
    def __init__(self, id, name, type, size, parent_id, custom_properties=None):
        self.id = str(id)
        self.name = name
        self.type = type
        self.size = size
        self.custom_properties = custom_properties
        self.parent_id = str(parent_id)

    def __str__(self):
        return "%s - name: %s, type: %s, parent: %s, props: %s" % (
            self.id,
            self.name,
            self.type,
            self.parent_id,
            self.custom_properties
        )

class FWAdminClient(object):

    ExitStatusDescription = {
        0: ("kExitOK", "No Error"),
        100: ("kExitUnknownError", "Unknown Error"),
        101: ("kExitFilesetNotExists", "The given fileset does not exist"),
        102: ("kExitClientNotExists", "The given client does not exist"),
        103: ("kExitGroupNotExists", "The given group does not exist"),
        104: ("kExitTargetIsNotGroup", "The given target does not exist"),
        105: ("kExitDBError", "Database internal error"),
        106: ("kExitFilesetUploadError", "Error while uploading fileset"),
        107: ("kExitModelUpdateError", "Error while updating the model"),
        108: ("kExitLoginError", "Login Error or Version Mismatch"),
        109: ("kExitImportFilesetError", "Error while importing a fileset"),
        110: ("kExitUnknownImportType", "Package type not supported for import"),
        111: ("kExitParseError", "Command line parse failed"),
        112: ("kExitAssociationToImagingFilesetError", "Can't create association with an imaging fileset"),
        113: ("kExitGroupCreationError", "Can't create a new fileset group"),
        114: ("kExitFilesetMergeError", "Cannot merge files in the fileset")
    }

    def __init__(self,
                 admin_name = 'fwadmin',
                 admin_pwd = 'filewave',
                 server_host = 'localhost',
                 server_port = 20016,
                 create_fs_callback=None,
                 remove_fs_callback=None,
                 print_output=False):

        self.fwadmin_executable = self.get_admin_tool_path()
        self.connection_options = ['-u', admin_name,
                                   '-p', admin_pwd,
                                   '-H', server_host,
                                   '-P', server_port ]

        self.print_output = print_output
        self.create_fs_callback = create_fs_callback
        self.remove_fs_callback = remove_fs_callback

    @classmethod
    def get_admin_tool_path(cls):
        systemName = platform.system()
        appPath = ''
        if 'Darwin' == systemName:
            appPath = "%s/FileWave Admin.app/Contents/MacOS/FileWave Admin"
        elif 'Windows' == systemName:
            appPath = '%s/RelWithDebInfo/FileWaveAdmin.exe'
        elif 'Linux' == systemName:
            appPath = '%s/FileWaveAdmin'
        else:
            raise Exception( 'Unsupported platform' )

        return appPath % cls.get_executable_path()

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

    def get_version(self):
        version = self.run_admin("-v")
        return version

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
        args = ['--createAssociation', '--clientgroup', client_id, '--fileset', fileset_id]
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
            options.extend(["--filesetgroup", str(target)])

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
            options.extend(["--filesetgroup", str(target)])

        import_package_result = self.run_admin(options)
        matcher = re.compile(r'new fileset with ID (?P<id>.+) was created')
        search = matcher.search(import_package_result)
        id = search.group('id')
        if self.create_fs_callback and hasattr(self.create_fs_callback, '__call__'):
            self.create_fs_callback(id)
        return id

    def set_property(self, fileset_id, prop_name, prop_value):
        options = ['--fileset', fileset_id, '--setProperty', '--key', prop_name, '--value', prop_value]
        self.run_admin(options)

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
            options.extend(["--filesetgroup", str(target)])
        create_empty_fileset_result = self.run_admin(options)
        print create_empty_fileset_result
        matcher = re.compile(r'new fileset (?P<id>.+) created with name (?P<name>.+)')
        search = matcher.search(create_empty_fileset_result)
        id = search.group('id')
        if self.create_fs_callback and hasattr(self.create_fs_callback, '__call__'):
            self.create_fs_callback(id)
        return id
