# TODO: improve docstring format
import time
import pytest

from cloudify_tester import config as cloudify_tester_config
from cloudify_tester.helpers.env import TestEnvironment
from cloudify_tester.helpers.logger import TestLogger

test_env_logger = TestLogger(
    log_path=None,
    logger_name='test_env_logger',
    log_format='%(message)s',
)
test_env_logger.console_logging_set_level('debug')


def pytest_addoption(parser):
    """
        Add the --cloudify-tester-config option to pytest.
    """
    parser.addoption(
        '--cloudify-tester-config',
        action='store',
        default='test_config.yaml',
        help='Location of the cloudify tester config.',
    )


@pytest.fixture(scope='module')
def tester_conf(config_file_location):
    """
        Retrieve the cloudify tester config.
    """
    schemas = cloudify_tester_config.default_schemas

    tester_conf = cloudify_tester_config.Config(
        config_files=[config_file_location],
        config_schema_files=schemas,
        logger=test_env_logger,
    )

    return tester_conf


@pytest.fixture(scope='module')
def environment(request, tester_conf):
    """
        Create a test environment.

        When pytest is finished, this test environment may be cleaned up
        depending on the result of the tests and on the test config.
    """
    # Make a somewhat helpful prefix for the tempdir
    workdir_prefix = generate_workdir_prefix(request.node.name)

    test_env = TestEnvironment()

    test_env.start(
        logging_level=tester_conf['logging']['level'],
        log_to_console=tester_conf['logging']['to_console'],
        workdir_prefix=workdir_prefix,
    )

    yield test_env

    testsfailed = 0
    # TODO: This is used in two places, factor it out
    module_tests = [item for item in request.session.items
                    if item.parent == request.node]

    for test in module_tests:
        if hasattr(test, '__scenario_report__'):
            for item in test.__scenario_report__.step_reports:
                if item.failed:
                    testsfailed += 1

    cleanup(
        test_env,
        tester_conf,
        testsfailed,
    )


@pytest.fixture(scope='module')
def config_file_location(request):
    """
        Get the config file location, as provided to pytest.
    """
    return request.config.getoption('--cloudify-tester-config')


def generate_workdir_prefix(test_name):
    """
        Generate a prefix for the temporary directory that the test will use.
    """
    # Brute forcey cleanup of test name to make for easier name on filesystem
    test_name = ''.join([
        char if char.isalnum() else '_' for char in test_name
    ][:10])
    workdir_prefix = '{prefix}_{feature}_{time}_'.format(
        prefix='cloudify_tester',
        feature=test_name,
        time=time.strftime('%d%b%H.%M'),
    )
    return workdir_prefix


def cleanup(environment, tester_conf, test_failure_count):
    """
        Clean up the test environment and/or delete the temp directory
        depending on the result of the tests and on the test config.
    """
    test_env_logger.info('Executing cleanup modules')
    test_env_logger.info(
        'Output will be absent if logging.to_console is false'
    )

    if test_failure_count > 0:
        run_cleanup = tester_conf['cleanup']['on_failure']
        remove_workdir = tester_conf['cleanup']['remove_workdir_on_failure']
    else:
        run_cleanup = tester_conf['cleanup']['on_success']
        remove_workdir = tester_conf['cleanup']['remove_workdir_on_success']
    environment.teardown(
        run_cleanup=run_cleanup,
        remove_workdir=remove_workdir,
    )
    if not remove_workdir:
        test_env_logger.info('Workdir remains in {location}'.format(
            location=environment.workdir,
        ))
