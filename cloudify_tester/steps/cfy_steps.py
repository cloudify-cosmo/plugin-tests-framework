from cloudify_tester.utils import get_repo_root
from pytest_bdd import given, when, parsers
from jinja2 import Template
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


@when(parsers.parse(
    "I have {blueprint_or_inputs} {name} from template {template_name}"
))
def blueprint_or_inputs(blueprint_or_inputs,
                        name,
                        template_name,
                        environment,
                        tester_conf):
    """
        Parse a blueprint or inputs template with values from the config.
        The template opened will be:
        (root of git repo)/system_tests/templates/<template_name>
        The parsed template will be placed in the test's workdir in a file
        with the <name> specified.
    """
    valid = [
        'blueprint',
        'inputs',
    ]

    if blueprint_or_inputs not in valid:
        raise ValueError(
            '{value} is invalid for creating blueprint or inputs. '
            'Valid options are {options}'.format(
                value=blueprint_or_inputs,
                options=', '.join(valid),
            )
        )

    destination = name

    repo_root = get_repo_root()

    # Find templates
    # TODO: This should be a utils class
    templates = {}
    templates_path = os.path.join(
        repo_root,
        'system_tests',
        'templates',
    )

    if os.path.isdir(templates_path):
        # Get a list of files in the template path root and any subdirs
        template_paths = [(path[0][len(templates_path):].lstrip('/'), path[2])
                          for path in os.walk(templates_path)]

        for template_location, template_names in template_paths:
            for template in template_names:
                key = '{loc}/{name}'.format(
                    loc=template_location,
                    name=template,
                )
                templates[key] = os.path.join(
                    templates_path,
                    template_location,
                    template,
                )

    template_path = templates[template_name]
    with open(template_path) as template_handle:
        template = Template(template_handle.read())

    template_conf = dict(tester_conf.items())
    template_conf['magic']['workdir'] = environment.workdir
    template_conf['magic']['repo_root'] = get_repo_root()

    result = template.render(template_conf)

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
        {blueprint_or_inputs}...' steps.
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


# TODO: This isn't a cfy step, move it
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
