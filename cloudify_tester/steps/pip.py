from pytest_bdd import when, parsers


@when(parsers.parse("I pip install {path}"))
def pip_install(environment, path):
    """
        Install a package into the python environment using pip.
    """
    environment.pip.install(path)
