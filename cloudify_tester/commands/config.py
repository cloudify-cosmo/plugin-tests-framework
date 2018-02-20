import click

# Note: While config files are in yaml, using yaml.dump adds a newline with an
# ellipsis. JSON will be compatible, but doesn't add fluff.
import json
import sys

from cloudify_tester.utils import NotInRepositoryError
try:
    from cloudify_tester.commands.utils import load_config
    from cloudify_tester.config import NotSet
except NotInRepositoryError as err:
    sys.stderr.write(
        'This must be run in the git repository that is being tested.\n'
        '{error}\n'.format(error=str(err))
    )
    sys.exit(1)


@click.group(
    name='config',
    short_help='Config tools- e.g. show schema or generate sample config.',
)
def config_group():
    pass


@config_group.command(
    short_help='Show the config schema.',
)
def schema():
    # TODO docstring
    config = load_config()

    show_entries(config.schema, False)


@config_group.command(
    short_help='Generate a sample config.',
)
def generate():
    # TODO docstring
    config = load_config()

    show_entries(config.schema, True)


@config_group.command(
    short_help='Validate the test config.',
)
# TODO: This is done several times. Make it better.
# also make the help message include default+envvar
@click.option(
    '--config', '-c',
    envvar='CLOUDIFY_PLUGIN_TESTS_CONFIG',
    default='test_config.yaml',
    help='Config file to validate.',
)
def validate(config):
    # TODO docstring
    config = load_config(config)

    namespaces = config.namespaces
    not_set_message = '{key} is not set and has no default!\n'
    magic_set_message = (
        '{key} is set. This will be ignored, as magic values cannot be '
        'configured.\n'
    )
    for namespace in namespaces:
        if namespace is None:
            check = config.items()
        else:
            check = config[namespace].items()
        for key, value in check:
            display_key = key
            if namespace is not None:
                display_key = '.'.join([namespace, key])
            if key not in namespaces:
                if namespace == 'magic':
                    if value is not NotSet:
                        sys.stderr.write(magic_set_message.format(
                            key=display_key,
                        ))
                else:
                    if value is NotSet:
                        sys.stderr.write(not_set_message.format(
                            key=display_key,
                        ))


def show_entries(schema, generate_sample_config=False, indent=''):
    sorted_config_entries = schema.keys()
    sorted_config_entries = [
        entry for entry in sorted_config_entries
        if isinstance(schema[entry], dict)
    ]
    sorted_config_entries.sort()

    namespaces = [
        entry for entry in sorted_config_entries
        if schema[entry].get('.is_namespace', False)
    ]
    if generate_sample_config and 'magic' in namespaces:
        namespaces.remove('magic')
        sorted_config_entries.remove('magic')
    root_config_entries = [
        entry for entry in sorted_config_entries
        if entry not in namespaces
    ]

    for config_entry in root_config_entries:
        details = schema[config_entry]
        if generate_sample_config:
            if 'default' in details.keys():
                print(indent + '{entry}: {default}'.format(
                    entry=config_entry,
                    default=json.dumps(details['default'])
                ))
            else:
                print(indent + '{entry}: '.format(entry=config_entry))
        else:
            line = '{entry}: {description}'
            if 'default' in schema[config_entry].keys():
                line = line + ' (Default: {default})'
            line = line.format(
                entry=config_entry,
                description=details['description'],
                default=json.dumps(details.get('default')),
            )
            print(indent + line)

    for namespace in namespaces:
        print(indent + namespace + ':')
        show_entries(
            schema[namespace],
            generate_sample_config,
            indent + '  ',
        )
