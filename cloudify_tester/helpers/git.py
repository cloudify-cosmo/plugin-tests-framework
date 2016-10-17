import os


class GitHelper(object):
    def __init__(self, workdir, executor):
        self.workdir = workdir
        self._executor = executor

    def _exec(self, command, repo_path, fake_run=False):
        prepared_command = ['git']
        prepared_command.extend(command)

        repo_path = os.path.join(self.workdir, repo_path)

        return self._executor(prepared_command, cwd=repo_path,
                              fake=fake_run)

    def clone(self, repository, clone_to=None, fake_run=False):
        if not clone_to:
            # Clone to the repo name if no clone_to is provided
            clone_to = os.path.split(repository)[-1]

        path = os.path.join(self.workdir, clone_to)
        # This might want to be an is_dir check to give better error messages
        if not os.path.exists(path):
            os.mkdir(path)

        # We clone to 'current dir' in the repo path to simplify self._exec
        return self._exec(['clone', repository, '.'], repo_path=clone_to,
                          fake_run=fake_run)

    def checkout(self, repo_path, checkout, fake_run=False):
        return self._exec(['checkout', checkout], repo_path=repo_path,
                          fake_run=fake_run)

    def get_current_repo_root(self):
        """
            From the current working directory, find the root of the repo we're in.
        """
        return self._executor(['rev-parse', '--show-toplevel'])
