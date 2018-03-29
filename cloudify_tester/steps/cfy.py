from cloudify_tester.utils import (
    get_rendered_template,
    render_template,
)
from pytest_bdd import given, when, then, parsers
import json
import os
import yaml


@when(parsers.parse(
    "I have installed cfy {version}"
))
def install_cli(version, environment, tester_conf):
    """
        Ensure that the cloudify package is installed, from a source defined
        in the test config.
    """
    # Work with multiple scenarios in the same feature, rather than
    # failing due to already being installed
    if not environment.cli_installed:
        environment.cfy.pip_install(version=version)
        environment.cli_installed = True
    # Make sure we use profiles in the test dir only
    os.environ['CFY_WORKDIR'] = environment.workdir


@when("I have installed cfy")
def install_default_cli(environment, tester_conf):
    """
        Ensure that the version of cloudify defined in the test config is
        installed, using the version from cloudify.default_version
    """
    install_cli(
        tester_conf['cloudify']['default_version'],
        environment,
        tester_conf,
    )


@given("I have a healthy manager")
def check_existing_healthy_manager(environment, tester_conf):
    """
        Confirm that we have a pre-existing healthy manager.
    """
    use_pre_existing_manager(environment, tester_conf)
    check_manager_is_healthy(environment)


@given("I use my existing manager")
def use_pre_existing_manager(environment, tester_conf):
    """
        Set cfy to use a pre-existing manager.
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


@when("I use cfy profile for {manager}")
def use_manager(manager_name, environment):
    """
        Set cfy to use a manager that has been deployed by the framework.
    """
    assert manager_name in environment.managers, (
        'Manager {selected} was not created by this test run. '
        'Available managers are: {available}'.format(
            selected=manager_name,
            available=', '.join(environment.managers.keys()),
        )
    )

    manager = environment.managers[manager_name]

    environment.add_cleanup(
        environment.cfy.profiles.delete,
        kwargs={
            'profile_name': manager['ip'],
        },
    )

    environment.cfy.profiles.use(
        ip=manager['ip'],
        username=manager['username'],
        password=manager['password'],
        rest_certificate=manager['certificate_path'],
    )


@when("My current manager is healthy")
def check_manager_is_healthy(environment):
    """
        Check the currently selected manager is healthy.
    """
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
    "I create tenant {tenant_name} with user with password {password}"
))
def create_tenant(tenant_name, password, environment):
    """
        Create a new tenant with the given name, and a user of the same name
        with access to only that tenant.
        This will automatically add a cleanup to the environment for the
        created resources.
    """
    environment.add_cleanup(
        environment.cfy.tenants.delete,
        kwargs={
            'tenant_name': tenant_name,
        },
    )
    environment.cfy.tenants.create(tenant_name=tenant_name)

    environment.add_cleanup(
        environment.cfy.users.delete,
        kwargs={
            'username': tenant_name,
        },
    )
    environment.cfy.users.create(
        role='user',
        password=password,
        username=tenant_name,
    )

    environment.add_cleanup(
        environment.cfy.tenants.remove_user,
        kwargs={
            'username': tenant_name,
            'tenant_name': tenant_name,
        },
    )
    environment.cfy.tenants.add_user(tenant_name=tenant_name,
                                     username=tenant_name)


@when(parsers.parse(
    "I switch to tenant {tenant_name} using user using password {password}"
))
def switch_tenant(tenant_name, password, environment, tester_conf):
    """
        Switch to a named tenant using the user of the same name, and the
        specified password.
        This will automatically switch back to the previous user during
        cleanup.
    """
    if hasattr(environment.cfy, '_current_user'):
        environment.add_cleanup(
            environment.cfy.profiles.set,
            kwargs=environment.cfy._current_user,
        )
    else:
        creds_conf = tester_conf['cloudify']
        environment.add_cleanup(
            environment.cfy.profiles.set,
            kwargs={
                'tenant': 'default_tenant',
                'username': creds_conf['existing_manager_username'],
                'password': creds_conf['existing_manager_password'],
            },
        )

    environment.cfy._current_user = {
        'tenant': tenant_name,
        'username': tenant_name,
        'password': password,
    }

    environment.cfy.profiles.set(
        tenant=tenant_name,
        username=tenant_name,
        password=password,
    )


@when(parsers.parse(
    "I have {name} blueprint and inputs from templates"
))
def render_named_blueprint_and_inputs(name, environment, tester_conf):
    """
        Render blueprint and inputs templates for a given name.
        This will use templates/blueprints/{name} for the blueprint
        and templates/inputs/{name} for the inputs.
        The files will be rendered as {name}.yaml and {name}_inputs.yaml,
        respectively.
    """
    blueprint_or_inputs(
        'blueprint',
        name='{name}.yaml'.format(name=name),
        template_name='blueprints/{name}'.format(name=name),
        environment=environment,
        tester_conf=tester_conf,
    )
    blueprint_or_inputs(
        'inputs',
        name='{name}_inputs.yaml'.format(name=name),
        template_name='inputs/{name}'.format(name=name),
        environment=environment,
        tester_conf=tester_conf,
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


@when(parsers.parse(
    "I create secret {secret_name} with value {secret_value}"
))
def create_secret(secret_name, secret_value, environment):
    """
        Create a secret.
        This will automatically add a 'delete' cleanup to the environment.
    """
    environment.add_cleanup(
        environment.cfy.secrets.delete,
        kwargs={
            'secret_name': secret_name,
        },
    )
    environment.cfy.secrets.create(
        secret_name=secret_name,
        secret_value=secret_value,
    )


@when(parsers.parse(
    "I run the install workflow for deployment {deployment_id}"
))
def install(deployment_id, environment):
    """
        Run the install workflow on a given deployment on the manager.
        This will automatically add an 'uninstall' cleanup to the environment.
    """
    environment.add_cleanup(
        environment.cfy.executions.start,
        kwargs={
            'workflow': 'uninstall',
            'deployment_id': deployment_id,
        },
    )
    result = environment.cfy.executions.start(
        workflow='install',
        deployment_id=deployment_id,
    )
    assert result['returncode'] == 0, (
        'Install workflow failed for deployment {deployment_id}!'.format(
            deployment_id=deployment_id,
        )
    )


@when(parsers.parse(
    "I upload blueprint {blueprint_path} as {blueprint_id}"
))
def upload_blueprint(blueprint_path, blueprint_id, environment):
    """
        Upload a blueprint to a manager.
        This will automatically add a 'delete' cleanup to the environment.
    """
    environment.add_cleanup(
        environment.cfy.blueprints.delete,
        kwargs={
            'blueprint_id': blueprint_id,
        },
    )
    environment.cfy.blueprints.upload(
        blueprint_path=blueprint_path,
        blueprint_id=blueprint_id,
    )


@when(parsers.parse(
    "I create deployment {deployment_id} from blueprint {blueprint_id}"
))
def create_deployment(deployment_id, blueprint_id, environment):
    """
        Create a deployment from a blueprint on a manager.
        This will not validate plugins.
        This will automatically add a 'delete' cleanup to the environment.
    """
    environment.add_cleanup(
        environment.cfy.deployments.delete,
        kwargs={
            'deployment_id': deployment_id,
        },
    )
    environment.cfy.deployments.create(
        blueprint_id=blueprint_id,
        deployment_id=deployment_id,
        skip_plugins_validation=True,
    )


@given("I have installed the plugin locally")
def install_plugin_in_env(plugin_location, environment):
    environment.pip.install(plugin_location)


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
    environment.cfy.init(
        blueprint_file=blueprint,
        inputs_file=inputs,
    )


@when(parsers.parse(
    "I install local blueprint {blueprint}"
))
def local_install(blueprint, environment):
    """
        Run a workflow on a locally initialised blueprint.
        This will automatically add an 'uninstall' cleanup to the environment.
    """
    environment.add_cleanup(
        environment.cfy.executions.start,
        kwargs={
            'workflow_name': 'uninstall',
            'blueprint_file': blueprint,
            'local': True,
        },
    )
    result = environment.cfy.executions.start(
        workflow_name='install',
        blueprint_file=blueprint,
        local=True,
    )
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
    """
        Confirm a local output has a specified value.
    """
    outputs = environment.cfy.local.outputs()['cfy_outputs']
    # Make sure the comparisons are all string based, a different step should
    # be created that forces the parsed type to be of the correct type for
    # other types.
    assert str(outputs[output]) == value


@when(parsers.parse("I run the {operation} operation on local node {node}"))
def local_operation(operation, node, environment):
    """
        Run a local operation and complain on failure.
    """
    run_operation(operation, node, environment)


@when(parsers.parse(
    "I run the {operation} operation with kwargs on local node {node}, "
    "json args: {kwargs}"
))
def local_operation_with_args(operation, kwargs, node, environment):
    """
        Run a local operation with specified kwargs and complain on failure.
    """
    kwargs = json.loads(kwargs)
    run_operation(operation, node, environment, args=kwargs)


@when(parsers.parse("I fail the {operation} operation on local node {node}"))
def fail_local_operation(operation, node, environment):
    """
        Run a local operation with specified kwargs and complain on success.
    """
    run_operation(operation, node, environment, succeed=False)


@when(parsers.parse(
    "I fail the {operation} operation with kwargs on local node {node}, "
    "json args: {kwargs}"
))
def fail_local_operation_with_args(operation, kwargs, node, environment):
    """
        Run an operation with specified kwargs and complain on success.
    """
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
