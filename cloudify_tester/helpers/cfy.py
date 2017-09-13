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
        self.profiles = _CfyProfilesHelper(
            workdir=workdir,
            executor=executor,
        )
        self.tenants = _CfyTenantsHelper(
            workdir=workdir,
            executor=executor,
        )
        self.users = _CfyUsersHelper(
            workdir=workdir,
            executor=executor,
        )
        self.secrets = _CfySecretsHelper(
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

    def status(self, fake_run=False):
        command = ['status']
        result = self._exec(command, fake_run=fake_run)

        # Get the services in an easy to consume way
        output_lines = [line for line in result['stdout'] if '|' in line]
        # Get rid of the header
        output_lines = output_lines[1:]
        services = {}
        for line in output_lines:
            line = line.split('|')
            service_name = line[1].strip()
            service_status = line[2].strip()
            services[service_name] = service_status
        result['services'] = services

        return result


class _CfySecretsHelper(CfyHelperBase):
    def create(self, secret_name, secret_value, fake_run=False):
        return self._exec(
            [
                'secrets', 'create',
                '--secret-string', secret_value,
                secret_name,
            ],
            fake_run=fake_run,
        )


class _CfyProfilesHelper(CfyHelperBase):
    def use(self, ip, username, password, fake_run=False):
        return self._exec(
            [
                'profiles', 'use',
                '--manager-username', username,
                '--manager-password', password,
                ip,
            ],
            fake_run=fake_run,
        )

    def set(self, tenant=None, username=None, password=None, fake_run=False):
        command = ['profiles', 'set']
        if tenant:
            command.extend(['--manager-tenant', tenant])
        if username:
            command.extend(['--manager-username', username])
        if password:
            command.extend(['--manager-password', password])
        return self._exec(command, fake_run=fake_run)


class _CfyTenantsHelper(CfyHelperBase):
    def create(self, tenant_name, fake_run=False):
        return self._exec(
            [
                'tenants', 'create', tenant_name,
            ],
            fake_run=fake_run,
        )

    def add_user(self, tenant_name, username, fake_run=False):
        return self._exec(
            [
                'tenants', 'add-user',
                '--tenant-name', tenant_name,
                username,
            ],
            fake_run=fake_run,
        )


class _CfyUsersHelper(CfyHelperBase):
    def create(self, username, password, role='user', fake_run=False):
        return self._exec(
            [
                'users', 'create',
                '--security-role', role,
                '--password', password,
                username,
            ],
            fake_run=fake_run,
        )


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

    def execute_operation(self, operation, node, operation_kwargs=None,
                          fake_run=False, retries=50, interval=3):
        params = {'operation': operation, 'node_ids': node}
        if operation_kwargs:
            params['operation_kwargs'] = operation_kwargs
        return self._exec(
            [
                'local', 'execute', '--workflow', 'execute_operation',
                '--parameters', json.dumps(params),
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
            '--blueprint-id', blueprint_id,
            blueprint_path,
        ]
        if validate:
            command.append('--validate')
        return self._exec(command, fake_run=fake_run)

    def delete(self, blueprint_id, fake_run=False):
        return self._exec(
            [
                'blueprints', 'delete',
                blueprint_id,
            ],
            fake_run=fake_run,
        )


class _CfyDeploymentsHelper(CfyHelperBase):
    def create(self, blueprint_id, deployment_id, inputs_path=None,
               skip_plugins_validation=False, fake_run=False):
        command = [
            'deployments', 'create',
            '--blueprint-id', blueprint_id,
            deployment_id,
        ]
        if inputs_path is not None:
            command.extend(['--inputs', inputs_path])
        if skip_plugins_validation:
            command.append('--skip-plugins-validation')
        return self._exec(command, fake_run=fake_run)

    def delete(self, deployment_id, ignore_live_nodes=False, fake_run=False):
        command = [
            'deployments', 'delete',
            deployment_id,
        ]
        if ignore_live_nodes:
            command.append('--ignore-live-nodes')
        return self._exec(command, fake_run=fake_run)

    def outputs(self, deployment_id, fake_run=False):
        result = self._exec(
            ['deployment', 'outputs', deployment_id],
            fake_run=fake_run,
        )
        result['cfy_outputs'] = json.loads(str(''.join(result['stdout'])))
        return result


class _CfyPluginsHelper(CfyHelperBase):
    def upload(self, plugin_path, fake_run=False):
        command = ['plugins', 'upload', plugin_path]
        return self._exec(command, fake_run=fake_run)


class _CfyExecutionsHelper(CfyHelperBase):
    def start(self, deployment_id, workflow, timeout=900, fake_run=False):
        command = [
            'executions', 'start',
            '--deployment-id', deployment_id,
            '--timeout', timeout,
            workflow,
        ]
        return self._exec(command, fake_run=fake_run)
