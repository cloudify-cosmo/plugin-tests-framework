class CurlHelper(object):
    def __init__(self, workdir, executor):
        self.workdir = workdir
        self._executor = executor

    def _exec(self, command, fake_run=False):
        prepared_command = ['curl']
        prepared_command.extend(command)

        return self._executor(prepared_command, fake=fake_run)

    def get_file(self, url, dest_path, fake_run=False):
        return self._exec(['-o', dest_path, url], fake_run=fake_run)
