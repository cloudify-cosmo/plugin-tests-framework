import json
import os

import yaml


class CfyHelperBase(object):
    def __init__(self, workdir, executor):
        self.workdir = workdir
        self._executor = executor

    def _exec(self, command, install_plugins=False,
              retries=0, retry_delay=3, fake_run=False):
        prepared_command = ['bin/cfy']
        command = [str(component) for component in command]
        prepared_command.extend(command)
        if install_plugins:
            prepared_command.append('--install-plugins')
        return self._executor(
            prepared_command,
            retries=retries,
            retry_delay=retry_delay,
            path_prepends=['bin'],
            fake=fake_run,
        )


class CfyHelper(CfyHelperBase):
    def __init__(self, workdir, executor):
        super(CfyHelper, self).__init__(workdir=workdir, executor=executor)
        self.local = _CfyLocalHelper(workdir=workdir, executor=executor)
        self.blueprints = _CfyBlueprintsHelper(
            workdir=workdir,
            executor=executor
        )
        self.deployments = _CfyDeploymentsHelper(
            workdir=workdir,
            executor=executor,
        )
        self.executions = _CfyExecutionsHelper(
            workdir=workdir,
            executor=executor,
        )
        self.plugins = _CfyPluginsHelper(
            workdir=workdir,
            executor=executor,
        )

    def deploy_yaml(self, source_dict, file_name):
        yaml_dict = yaml.dump(source_dict, default_flow_style=False)
        self.deploy_file(yaml_dict, file_name)

    def deploy_file(self, data, file_name):
        dir_name, file_name = os.path.split(file_name)
        if dir_name != '':
            try:
                os.makedirs(os.path.join(self.workdir, dir_name))
            except OSError as err:
                if hasattr(err, 'errno') and err.errno == 17:
                    # Path already exists
                    pass
                else:
                    raise
        with open(os.path.join(self.workdir, dir_name, file_name),
                  'w') as output_handle:
            output_handle.write(data)

    def init(self, fake_run=False):
        return self._exec(['init'], fake_run=fake_run)

    def bootstrap(self, blueprint_path, inputs_path, install_plugins=False,
                  fake_run=False):
        return self._exec(
            [
                'bootstrap',
                '--blueprint-path', blueprint_path,
                '--inputs', inputs_path,
            ],
            install_plugins=install_plugins,
            fake_run=fake_run,
        )

    def teardown(self, ignore_deployments=False, fake_run=False):
        command = ['teardown', '-f']
        if ignore_deployments:
            command.append('--ignore-deployments')
        return self._exec(command, fake_run=fake_run)


class _CfyLocalHelper(CfyHelperBase):
    def init(self, blueprint_path, inputs_path, install_plugins=False,
             fake_run=False):
        return self._exec(
            [
                'local', 'init',
                '--blueprint-path', blueprint_path,
                '--inputs', inputs_path,
            ],
            install_plugins=install_plugins,
            fake_run=fake_run,
        )

    def execute_operation(self, operation, node, fake_run=False,
                          retries=50, interval=3):
        return self._exec(
            [
                'local', 'execute', '--workflow', 'execute_operation',
                '--parameters', json.dumps(
                    {'operation': operation, 'node_ids': node}
                ),
                '--task-retry-interval', interval,
                '--task-retries', retries,
            ],
            fake_run=fake_run,
        )

    def execute(self, workflow, fake_run=False, retries=50, interval=3):
        return self._exec(['local', 'execute', '--workflow', workflow,
                           '--task-retry-interval', interval,
                           '--task-retries', retries],
                          fake_run=fake_run)

    def outputs(self, fake_run=False):
        result = self._exec(['local', 'outputs'], fake_run=fake_run)
        result['cfy_outputs'] = json.loads(str(''.join(result['stdout'])))
        return result

    def instances(self, fake_run=False):
        result = self._exec(['local', 'instances'], fake_run=fake_run)
        result['cfy_instances'] = json.loads(str(''.join(result['stdout'])))
        return result


class _CfyBlueprintsHelper(CfyHelperBase):
    def upload(self, blueprint_path, blueprint_id, validate=False,
               fake_run=False):
        command = [
            'blueprints', 'upload',
            '--blueprint-path', blueprint_path,
            '--blueprint-id', blueprint_id,
        ]
        if validate:
            command.append('--validate')
        return self._exec(command, fake_run=fake_run)

    def delete(self, blueprint_id, fake_run=False):
        return self._exec(
            [
                'blueprints', 'delete',
                '--blueprint-id', blueprint_id,
            ],
            fake_run=fake_run,
        )


class _CfyDeploymentsHelper(CfyHelperBase):
    def create(self, blueprint_id, deployment_id, inputs_path=None,
               fake_run=False):
        command = [
            'deployments', 'create',
            '--blueprint-id', blueprint_id,
            '--deployment-id', deployment_id,
        ]
        if inputs_path is not None:
            command.extend(['--inputs', inputs_path])
        return self._exec(command, fake_run=fake_run)

    def delete(self, deployment_id, ignore_live_nodes=False, fake_run=False):
        command = [
            'deployments', 'delete',
            '--deployment-id', deployment_id,
        ]
        if ignore_live_nodes:
            command.append('--ignore-live-nodes')
        return self._exec(command, fake_run=fake_run)


class _CfyPluginsHelper(CfyHelperBase):
    def upload(self, plugin_path, fake_run=False):
        command = ['plugins', 'upload', '-p', plugin_path]
        return self._exec(command, fake_run=fake_run)


class _CfyExecutionsHelper(CfyHelperBase):
    def start(self, deployment_id, workflow, timeout=900, fake_run=False):
        command = [
            'executions', 'start',
            '--deployment-id', deployment_id,
            '--workflow', workflow,
            '--timeout', timeout,
        ]
        return self._exec(command, fake_run=fake_run)
