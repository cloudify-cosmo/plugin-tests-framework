from cloudify_tester.commands.utils import load_config, get_logger

import click

import subprocess
import sys


@click.command(
    short_help='Run the tests.',
)
@click.option(
    '--config', '-c',
    envvar='CLOUDIFY_PLUGIN_TESTS_CONFIG',
    default='test_config.yaml',
    help='Config file to use. '
         'If none is provided, tests requiring config will not run.',
)
def run(config):
    # TODO docstring
    config = load_config(config, missing_config_fail=False)
    logger = get_logger()

    try:
        subprocess.call(['tox', '--version'])
    except OSError:
        logger.warn('tox command not found, installing using pip.')
        subprocess.check_call(['pip', 'install', 'tox'])

    if config is None:
        test_groups = ['code-quality', 'internal']
        logger.warn(
            'As no config was supplied, only the following test groups '
            'will be run: {tests}'.format(tests=', '.join(test_groups))
        )
        ignore_quality_failures = False
    else:
        test_groups = config['test_groups']
        ignore_quality_failures = config['ignore_quality_failures']

    quality_failures_ignored = False
    for test_group in test_groups:
        command = ['tox', '-e', test_group]
        try:
            subprocess.check_call(command)
        except subprocess.CalledProcessError:
            if ignore_quality_failures and test_group == 'code-quality':
                logger.warn(
                    'There were code quality failures, but '
                    'ignore_quality_failures is set to true in the config.'
                )
                quality_failures_ignored = True
                continue
            this_group_pos = test_groups.index(test_group)
            successful_groups = test_groups[:this_group_pos]
            if quality_failures_ignored:
                successful_groups.remove('code-quality')
                logger.warn(
                    'The code-quality group had failures which were ignored.'
                )
            remaining_groups = test_groups[this_group_pos + 1:]

            if successful_groups:
                logger.info(
                    'These test groups passed: {groups}'.format(
                        groups=', '.join(successful_groups),
                    )
                )
            logger.error(
                'Failed running {group}, using command: {command}'.format(
                    group=test_group,
                    command=' '.join(command),
                )
            )
            if remaining_groups:
                logger.warn(
                    'The following test groups will not run until the '
                    'current failures are corrected: {groups}'.format(
                        groups=', '.join(remaining_groups),
                    )
                )
            sys.exit(1)
