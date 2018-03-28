from cloudify_tester.utils import get_config_entry
from pytest_bdd import given, then, when, parsers
import pytest
import json
import time


@given("no tests have failed in this feature")
def feature_has_not_failed_yet(request):
    """
        Stop running this scenario if any other scenarios have failed in this
        feature.
    """
    # TODO: This is used in two places, factor it out
    module_tests = [item for item in request.session.items
                    if item.parent == request.node.parent]

    for test in module_tests:
        if hasattr(test, '__scenario_report__'):
            for item in test.__scenario_report__.step_reports:
                assert not item.failed


@given(parsers.parse("I skip this test if {config_entry} is {truth}"))
def skip_test(config_entry, truth, tester_conf):
    """
        Skip this test if the specified configuration entry is {true|false}.
    """
    truth = json.loads(truth)
    assert isinstance(truth, bool)

    entry = get_config_entry(path=config_entry, config=tester_conf)

    if entry == truth:
        pytest.skip('{} was {}, so this test is skipped.'.format(config_entry,
                                                                 truth))


@then(parsers.cfparse("I wait {count:d} seconds"))
def wait(count):
    """
        Wait for {count} seconds.
    """
    time.sleep(count)


@when(parsers.cfparse("I download {url} on {user_at_host} as {filepath}"))
def download_file_on_host(url, user_at_host, filepath, environment,
                          tester_conf):
    """
        Download file from specified URL to given path on target user@host.
        This file download will be initiated using SSH.
    """
    run_command_on_host(
        command='curl -o {filepath} {url}'.format(
            filepath=filepath,
            url=url,
        ),
        user_at_host=user_at_host,
        environment=environment,
        tester_conf=tester_conf,
    )


@when(parsers.cfparse('I run SSH command "{command}" on {user_at_host}'))
def run_command_on_host(command, user_at_host, environment, tester_conf):
    """
        Run specified command on target user@host via SSH.
    """
    ssh_key = tester_conf['ssh']['key_path']
    ssh_command = [
        'ssh',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=ssh_known_hosts',
    ]
    if ssh_key:
        ssh_command.extend(['-i', ssh_key])
    ssh_command.extend([user_at_host, command])
    environment.executor(ssh_command)


@when(parsers.cfparse(
    'I copy {source_path} (to|from) {user_at_host} to {destination_path}'
))
def scp_file(source_path, user_at_host, destination_path, environment,
             tester_conf):
    """
       Copy a file via scp.
    """
    ssh_key = tester_conf['ssh']['key_path']
    scp_command = [
        'scp',
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=ssh_known_hosts',
    ]
    if ssh_key:
        scp_command.extend(['-i', ssh_key])
    scp_command.extend([user_at_host + ':' + source_path, destination_path])
    environment.executor(scp_command)
