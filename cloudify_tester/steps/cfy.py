from cloudify_tester.utils import get_repo_root, get_rendered_template
from pytest_bdd import given, when, then, parsers
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
    environment.cfy.local.execute('install')


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
    environment.cfy.local.execute('uninstall')


@then(parsers.parse("I confirm that local output {output} is {value}"))
def local_output_check(environment, output, value):
    outputs = environment.cfy.local.outputs()['cfy_outputs']
    # Make sure the comparisons are all string based, a different step should
    # be created that forces the parsed type to be of the correct type for
    # other types.
    assert str(outputs[output]) == value
