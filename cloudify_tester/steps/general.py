from cloudify_tester.utils import get_repo_root, get_config_entry
from pytest_bdd import given, when, parsers
import pytest
from jinja2 import Template
import os
import json


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


@given(parsers.parse("I skip this test if {config_entry} is {truth}"))
def skip_test(config_entry, truth, tester_conf):
    """
        Skip this test if the specified configuration entry is {true|false}.
    """
    truth = json.loads(truth)
    assert isinstance(truth, bool)

    entry = get_config_entry(path=config_entry, config=tester_conf)

    if entry == truth:
        pytest.skip('{} was {}, so this test is skipped.'.format(config_entry,
                                                                 truth))
