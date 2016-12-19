import subprocess


def get_repo_root():
    """
        Get the root of the git repo the cloudify_tester commands/tests are
        being run from.
    """
    return subprocess.check_output([
        'git', 'rev-parse', '--show-toplevel',
    ]).strip()


def get_config_entry(path, config):
    path = path.split('.')
    current_location = config
    for nested in path:
        current_location = current_location[nested]
    return current_location
