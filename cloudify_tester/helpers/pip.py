class PipHelper(object):
    def __init__(self, workdir, executor):
        self.workdir = workdir
        self._executor = executor

    def _exec(self, command, fake_run=False):
        prepared_command = ['bin/pip']
        prepared_command.extend(command)
        self._executor(prepared_command, fake=fake_run)

    def install(self, packages, upgrade=False, fake_run=False):
        if not isinstance(packages, list):
            packages = [packages]
        command = ['install']
        if upgrade:
            command.append('--upgrade')
        command.extend(packages)
        self._exec(command, fake_run=fake_run)

    def install_cloudify_cli(self, organisation, version, fake_run=False):
        command = [
            'install',
            'https://github.com/{organisation}/'
            'cloudify-cli/archive/{version}.zip'.format(
                organisation=organisation,
                version=version,
            ),
            '-r',
            'https://raw.githubusercontent.com/{organisation}/'
            'cloudify-cli/{version}/dev-requirements.txt'.format(
                organisation=organisation,
                version=version,
            ),
        ]
        self._exec(command, fake_run=fake_run)
