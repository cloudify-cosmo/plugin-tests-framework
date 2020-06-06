import click

from cloudify_tester.commands.config import config_group
from cloudify_tester.commands.template import template_group
from cloudify_tester.commands.run import run


@click.group()
def cloudify_tester():
    pass


cloudify_tester.add_command(config_group)
cloudify_tester.add_command(template_group)
cloudify_tester.add_command(run)
