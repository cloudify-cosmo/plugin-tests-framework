import os
import subprocess

from jinja2 import Template


class NotInRepositoryError(Exception):
    pass


def get_repo_root():
    """
        Get the root of the git repo the cloudify_tester commands/tests are
        being run from.
    """
    try:
        return subprocess.check_output([
            'git', 'rev-parse', '--show-toplevel',
        ]).strip()
    except subprocess.CalledProcessError as err:
        raise NotInRepositoryError(
            'Error trying to find repo root: {msg}'.format(msg=str(err))
        )


def get_config_entry(path, config):
    path = path.split('.')
    current_location = config
    for nested in path:
        current_location = current_location[nested]
    return current_location


def get_rendered_template(template_name, tester_conf, environment):
    template_data = get_template_data(template_name)

    return render_template(template_data, tester_conf, environment)


def render_template(template_data, tester_conf, environment):
    template = Template(template_data)
    template_conf = dict(tester_conf.items())
    template_conf['magic']['workdir'] = environment.workdir
    template_conf['magic']['repo_root'] = get_repo_root()

    return template.render(template_conf)


def get_template_data(template_name):
    templates = get_templates()

    template_path = templates[template_name]
    with open(template_path) as template_handle:
        template = template_handle.read()

    return template


def get_templates():
    repo_root = get_repo_root()

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
    return templates
