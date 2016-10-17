from cloudify_tester.commands.utils import load_config

import click
from jinja2 import Template


@click.group(
    name='template',
    short_help='Template tools- e.g. show parsed template.',
)
def template_group():
    pass


@template_group.command(
    short_help='Show template parse results with a given config.'
)
@click.argument(
    'template_path',
)
@click.option(
    '--config', '-c',
    envvar='CLOUDIFY_PLUGIN_TESTS_CONFIG',
    default='test_config.yaml',
    help='Config file to use for template generation.',
)
def parse(template_path, config):
    # TODO docstring
    config = load_config(config)

    # TODO: This logic should be somewhere more central as it is duplicated
    # in the steps
    with open(template_path) as template_handle:
        template = Template(template_handle.read())

    template_config = dict(config.items())
    template_config['magic']['workdir'] = '/path/to/your/workdir'

    print(template.render(template_config))
