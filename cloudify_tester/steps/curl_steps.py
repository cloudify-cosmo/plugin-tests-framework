from pytest_bdd import when, parsers


@when(parsers.parse("I download {url} to {location}"))
def download_file(environment, tester_conf, url, location):
    """
        Download the data located at the given url into the given local
        location.
    """
    if url.startswith('{{') and url.endswith('}}'):
        url = tester_conf[url.strip('{}')]
    environment.curl.get_file(url, location)
