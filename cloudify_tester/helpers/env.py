from cloudify_tester.helpers.cfy import CfyHelper
from cloudify_tester.helpers.curl import CurlHelper
from cloudify_tester.helpers.git import GitHelper
from cloudify_tester.helpers.pip import PipHelper
from cloudify_tester.helpers.logger import TestLogger
from cloudify_tester.helpers.executor import Executor

import os
import tempfile


class DangerousBugError(Exception):
    pass


class TestEnvironment(object):
    cfy = None
    git = None
    pip = None
    _cleanups = []
    manager_bootstrap_completed = False
    cli_installed = False
    plugins = []
    blueprints = []
    deployments = []
    deployments_outputs = {}
    _env_cache = {}

    def start(self,
              tester_conf,
              logging_level='debug',
              log_to_console=False,
              workdir_prefix='cloudify_tester'):
        self.workdir = tempfile.mkdtemp(prefix=workdir_prefix)

        # Set up logger
        self.logger = TestLogger(self.workdir)
        self.logger.file_logging_set_level(logging_level)
        if log_to_console:
            self.logger.console_logging_set_level(logging_level)
        else:
            self.logger.console_logging_disable()
        self.tester_conf = tester_conf

        self.executor = Executor(workdir=self.workdir, logger=self.logger,
                                 tester_conf=tester_conf)
        self.cfy = CfyHelper(workdir=self.workdir, executor=self.executor)
        self.git = GitHelper(workdir=self.workdir, executor=self.executor)
        self.pip = PipHelper(workdir=self.workdir, executor=self.executor)
        self.curl = CurlHelper(workdir=self.workdir, executor=self.executor)

        self.executor(['virtualenv', '.'])

    def add_cleanup(self, function, args=None, kwargs=None):
        cleanup = {
            'function': function,
        }
        if args is not None:
            cleanup['args'] = args
        if kwargs is not None:
            cleanup['kwargs'] = kwargs
        self._cleanups.append(cleanup)

    def remove_cleanup(self, function, args=None, kwargs=None):
        cleanup = {
            'function': function,
        }
        if args is not None:
            cleanup['args'] = args
        if kwargs is not None:
            cleanup['kwargs'] = kwargs
        self._cleanups.remove(cleanup)

    def teardown(self, run_cleanup=True, remove_workdir=True):
        # Cleanups should be run in reverse to clean up the last entity that
        # was added to the stack first
        for cleanup in reversed(self._cleanups):
            func = cleanup['function']
            args = cleanup.get('args', [])
            kwargs = cleanup.get('kwargs', {})
            kwargs['fake_run'] = not run_cleanup
            result = func(*args, **kwargs)
            if not run_cleanup:
                cleanup_intent_path = os.path.join(self.workdir,
                                                   'cleanup_intent.log')
                with open(cleanup_intent_path, 'a') as cleanup_intent_handle:
                    cleanup_intent_handle.write('{command}\n'.format(
                        command=result,
                    ))

        # This will break on a Mac (and Windows), so should have a better
        # check, but it probably wants something just to avoid major pain on
        # a single typo in a later commit
        if not self.workdir.startswith(tempfile.gettempdir()):
            raise DangerousBugError(
                'An attempt was made to delete something not in a temp '
                'directory. Target was: {path}'.format(
                    path=self.workdir,
                )
            )
        else:
            fake = not remove_workdir
            self.executor(['rm', '-rf', self.workdir], cwd='/tmp', fake=fake)
