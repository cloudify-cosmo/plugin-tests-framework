from cloudify_tester.utils import (
    get_repo_root,
    get_rendered_template,
    render_template,
)
from pytest_bdd import given, when, then, parsers
import json
import os
import yaml


@given("I have installed cfy")
def install_cli(environment, tester_conf):
    """
        Ensure that the cloudify package is installed, from a source defined
        in the test config.
    """
    # Work with multiple scenarios in the same feature, rather than
    # failing due to already being installed
    if not environment.cli_installed:
        environment.pip.install(tester_conf['cloudify']['install_cfy_from'])
        environment.cli_installed = True
    # Make sure we use profiles in the test dir only
    os.environ['CFY_WORKDIR'] = environment.workdir


@given("I have a healthy manager")
def check_existing_healthy_manager(environment, tester_conf):
    """
        Confirm that we have a pre-existing healthy manager.
    """
    assert tester_conf['cloudify']['existing_manager_ip'], (
        'Config entry cloudify.existing_manager_ip is not set. '
        'This must be set to use an existing manager.'
    )

    environment.cfy.profiles.use(
        ip=tester_conf['cloudify']['existing_manager_ip'],
        username=tester_conf['cloudify']['existing_manager_username'],
        password=tester_conf['cloudify']['existing_manager_password'],
    )

    status = environment.cfy.status()
    assert status['services'], (
        'There appear to be no services, which is not healthy for a manager.'
    )
    assert all(
        service_status == 'running'
        for service_status in status['services'].values()
    ), (
        'Not all services are in a running state. Manager is unhealthy.'
    )


@when(parsers.parse(
    "I have {file_type} {name} from template {template_name}"
))
def blueprint_or_inputs(file_type,
                        name,
                        template_name,
                        environment,
                        tester_conf):
    """
        Parse a blueprint, inputs, or script template with values from the
        config.
        The template opened will be:
        (root of git repo)/system_tests/templates/<template_name>
        The parsed template will be placed in the test's workdir in a file
        with the <name> specified.
    """
    valid = [
        'blueprint',
        'inputs',
        'script',
    ]

    if file_type not in valid:
        raise ValueError(
            '{value} is invalid for creating blueprint, script, or inputs. '
            'Valid options are {options}'.format(
                value=file_type,
                options=', '.join(valid),
            )
        )

    destination = name

    result = get_rendered_template(template_name, tester_conf, environment)

    if file_type == 'script':
        environment.cfy.deploy_file(result, destination)
    else:
        result = yaml.load(result)

        environment.cfy.deploy_yaml(result, destination)


@given("I have installed the plugin locally")
def install_plugin_in_env(environment):
    environment.pip.install(get_repo_root())


@when(parsers.parse(
    "I locally initialise blueprint {blueprint} with inputs {inputs}"
))
def local_init_blueprint(blueprint, inputs, environment):
    """
        Initialise the test environment's cfy local with the specified
        blueprint and input files, which are expected to be located in the
        test environment.
        These files should have been created with the 'I have
        {file_type}...' steps.
    """
    # TODO: This should use get_<x>_location classs from utils
    environment.cfy.local.init(
        blueprint_path=blueprint,
        inputs_path=inputs,
    )


@when("I run the local install workflow")
def local_install(environment):
    """
        Run the test environment's cfy local execute -w install.
        This will automatically add an 'uninstall' cleanup to the environment.
    """
    environment.add_cleanup(
        environment.cfy.local.execute,
        args=['uninstall'],
    )
    result = environment.cfy.local.execute('install')
    assert result['returncode'] == 0, (
        'Install workflow failed!'
    )


@when("I fail the local install workflow")
def fail_local_install(environment):
    """
        Run the test environment's cfy local execute -w install,
        and complain if it succeeds.
        Otherwise, the stderr and stdout will be available for checking with
        the "install workflow errors include <string>" step.
    """
    environment.add_cleanup(
        environment.cfy.local.execute,
        args=['uninstall'],
    )
    result = environment.cfy.local.execute('install')
    assert result['returncode'] != 0, (
        'Install workflow succeeded, but should have failed!'
    )

    environment.install_result = result


@then(parsers.parse(
    "case {sensitive_or_insensitive} install workflow errors have config "
    "value {value}"
))
def config_value_in_install_output(sensitive_or_insensitive, value,
                                   tester_conf, environment):
    """
        Check that a given config value specified appears in the install
        workflow output.

        e.g. if the config contained cloudify.types_location which was set to
        https://www.example.com/example_types.yaml
        then calling this with cloudify.types_location would try to confirm
        that the URL specified appeared in the install workflow output.
    """
    case_sensitive = sensitive_or_insensitive == 'sensitive'
    value = '{{' + value + '}}'
    value = render_template(value, tester_conf, environment)
    check_value_in_install_output(value, environment, case_sensitive)


@then(parsers.parse(
    "case {sensitive_or_insensitive} install workflow errors include {value}"
))
def string_in_install_output(sensitive_or_insensitive, value, environment):
    """
        Check that a given string appears in the install workflow output.
    """
    case_sensitive = sensitive_or_insensitive == 'sensitive'
    check_value_in_install_output(value, environment, case_sensitive)


def check_value_in_install_output(value, environment, case_sensitive):
    # Yes, this is checking stdout, because that's where cfy puts the error
    output = ''.join(environment.install_result['stdout'])
    if not case_sensitive:
        value = value.lower()
        output = output.lower()
    assert value in output, (
        'Expected value not found in install workflow output!'
    )


@when("I run the local uninstall workflow")
def local_uninstall(environment):
    """
        Run the test environment's cfy local execute -w install.
        This will automatically remove the 'uninstall' cleanup from the
        environment.
    """
    environment.remove_cleanup(
        environment.cfy.local.execute,
        args=['uninstall'],
    )
    result = environment.cfy.local.execute('uninstall')
    assert result['returncode'] == 0, (
        'Uninstall workflow failed!'
    )


@then(parsers.parse("I confirm that local output {output} is {value}"))
def local_output_check(environment, output, value):
    outputs = environment.cfy.local.outputs()['cfy_outputs']
    # Make sure the comparisons are all string based, a different step should
    # be created that forces the parsed type to be of the correct type for
    # other types.
    assert str(outputs[output]) == value


@when(parsers.parse("I run the {operation} operation on local node {node}"))
def local_operation(operation, node, environment):
    run_operation(operation, node, environment)


@when(parsers.parse(
    "I run the {operation} operation with kwargs on local node {node}, "
    "json args: {kwargs}"
))
def local_operation_with_args(operation, kwargs, node, environment):
    kwargs = json.loads(kwargs)
    run_operation(operation, node, environment, args=kwargs)


@when(parsers.parse("I fail the {operation} operation on local node {node}"))
def fail_local_operation(operation, node, environment):
    run_operation(operation, node, environment, succeed=False)


@when(parsers.parse(
    "I fail the {operation} operation with kwargs on local node {node}, "
    "json args: {kwargs}"
))
def fail_local_operation_with_args(operation, kwargs, node, environment):
    kwargs = json.loads(kwargs)
    run_operation(operation, node, environment, args=kwargs, succeed=False)


def run_operation(operation, node, environment, args=None, succeed=True):
    result = environment.cfy.local.execute_operation(
        operation=operation,
        operation_kwargs=args,
        node=node,
    )
    if succeed:
        assert result['returncode'] == 0, (
            'Operation failed!'
        )
    else:
        assert result['returncode'] != 0, (
            'Operation succeeded, but should have failed!'
        )
        environment.operation_result = result


def check_value_in_operation_output(value, environment, case_sensitive):
    output = ''.join(environment.operation_result['stdout'])
    if not case_sensitive:
        value = value.lower()
        output = output.lower()
    assert value in output, (
        'Expected value not found in operation output!'
    )


@then(parsers.parse(
    "case {sensitive_or_insensitive} operation errors have config "
    "value {value}"
))
def config_value_in_operation_output(sensitive_or_insensitive, value,
                                     tester_conf, environment):
    """
        Check that a given config value specified appears in the most recent
        operation output.

        e.g. if the config contained cloudify.types_location which was set to
        https://www.example.com/example_types.yaml
        then calling this with cloudify.types_location would try to confirm
        that the URL specified appeared in the most recent operation output.
    """
    case_sensitive = sensitive_or_insensitive == 'sensitive'
    value = '{{' + value + '}}'
    value = render_template(value, tester_conf, environment)
    check_value_in_operation_output(value, environment, case_sensitive)


@then(parsers.parse(
    "case {sensitive_or_insensitive} operation errors include {value}"
))
def string_in_operation_output(sensitive_or_insensitive, value, environment):
    """
        Check that a given string appears in the most recent operation output.
    """
    case_sensitive = sensitive_or_insensitive == 'sensitive'
    check_value_in_operation_output(value, environment, case_sensitive)
