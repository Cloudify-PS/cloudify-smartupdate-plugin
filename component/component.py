# Copyright (c) 2017-2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import CloudifyClientError

from .constants import (
    EXTERNAL_RESOURCE,
    TASK_RETRIES)
from cloudify_types.component.polling import (
    poll_with_timeout,
    is_all_executions_finished,
)
from cloudify_types.component.utils import (
    deployment_id_exists,
    update_runtime_properties,
    populate_runtime_with_wf_results
)
from cloudify_types.component.component import Component as BasicComponent


class Component(BasicComponent):

    def __init__(self, operation_inputs):
        super(Component, self).__init__(operation_inputs)

    def _http_client_wrapper(self,
                             option,
                             request_action,
                             request_args=None):
        """
        wrapper for http client requests with CloudifyClientError custom
        handling.
        :param option: can be blueprints, executions and etc.
        :param request_action: action to be done, like list, get and etc.
        :param request_args: args for the actual call.
        :return: The http response.
        """
        request_args = request_args or dict()
        generic_client = getattr(self.client, option)
        option_client = getattr(generic_client, request_action)

        try:
            return option_client(**request_args)
        except CloudifyClientError as ex:
            raise NonRecoverableError(
                'Client action "{0}" failed: {1}.'.format(request_action,
                                                          ex))

    def create_deployment(self):
        self._set_secrets()
        self._upload_plugins()

        if 'deployment' not in ctx.instance.runtime_properties:
            ctx.instance.runtime_properties['deployment'] = dict()

        if self.deployment_auto_suffix:
            self.deployment_id = self._generate_suffix_deployment_id(
                self.client, self.deployment_id)
        elif deployment_id_exists(self.client, self.deployment_id):
            ctx.logger.warn(
                'Deployment ID {0} exists. '
                'Will use.'.format(
                    self.blueprint_id))
            return False
        self._inter_deployment_dependency['target_deployment'] = \
            self.deployment_id

        update_runtime_properties('deployment', 'id', self.deployment_id)
        ctx.logger.info('Creating "{0}" component deployment.'
                        .format(self.deployment_id))

        self._http_client_wrapper('deployments', 'create', {
            'blueprint_id': self.blueprint_id,
            'deployment_id': self.deployment_id,
            'inputs': self.deployment_inputs
        })

        self._http_client_wrapper('inter_deployment_dependencies',
                                  'create',
                                  self._inter_deployment_dependency)

        # Prepare executions list fields
        execution_list_fields = ['workflow_id', 'id']

        # Call list executions for the current deployment
        executions = self._http_client_wrapper('executions', 'list', {
            'deployment_id': self.deployment_id,
            '_include': execution_list_fields
        })

        # Retrieve the ``execution_id`` associated with the current deployment
        execution_id = [execution.get('id') for execution in executions
                        if (execution.get('workflow_id') ==
                            'create_deployment_environment')]

        # If the ``execution_id`` cannot be found raise error
        if not execution_id:
            raise NonRecoverableError(
                'No execution Found for component "{}"'
                ' deployment'.format(self.deployment_id)
            )

        # If a match was found there can only be one, so we will extract it.
        execution_id = execution_id[0]
        ctx.logger.info('Found execution id "{0}" for deployment id "{1}"'
                        .format(execution_id,
                                self.deployment_id))
        return self.verify_execution_successful(execution_id)

    def execute_workflow(self):
        # Wait for the deployment to finish any executions
        if not poll_with_timeout(lambda:
                                 is_all_executions_finished(
                                     self.client, self.deployment_id),
                                 timeout=self.timeout,
                                 expected_result=True):
            return ctx.operation.retry(
                'The "{0}" deployment is not ready for execution.'.format(
                    self.deployment_id))

        # we must to run some execution
        if not self.deployment.get(EXTERNAL_RESOURCE):

            # If the target deployment has the smart_update workflow defined,
            # execute it
            # If not, skip
            if self.workflow_id == 'smart_update':
                request_args = \
                    dict(deployment_id=self.deployment_id)
                deployment = self._http_client_wrapper(
                    'deployments', 'get', request_args)
                ctx.logger.debug('Get deployment response: {}'.format(
                    deployment
                ))
                workflows_names_list = []
                for workflow in deployment.get('workflows'):
                    workflows_names_list.append(workflow.get('name'))
                if 'smart_update' not in workflows_names_list:
                    ctx.logger.debug(
                        """Target deployment doesn't support smart_update.
                        Skipping."""
                    )
                    return

        execution_args = self.config.get('executions_start_args', {})

        request_args = dict(
            deployment_id=self.deployment_id,
            workflow_id=self.workflow_id,
            **execution_args
        )
        if self.workflow_id == ctx.workflow_id:
            request_args.update(dict(parameters=ctx.workflow_parameters))

        ctx.logger.info('Starting execution for "{0}" deployment'.format(
            self.deployment_id))
        execution = self._http_client_wrapper(
            'executions', 'start', request_args)

        ctx.logger.debug('Execution start response: "{0}".'.format(execution))

        execution_id = execution['id']
        if not self.verify_execution_successful(execution_id):
            ctx.logger.error('Execution {0} failed for "{1}" '
                             'deployment'.format(execution_id,
                                                 self.deployment_id))

        ctx.logger.info('Execution succeeded for "{0}" deployment'.format(
            self.deployment_id))
        populate_runtime_with_wf_results(self.client, self.deployment_id)
        return True

    def execute_deployment_update(self):
        # Wait for the deployment to finish any executions
        if not poll_with_timeout(lambda:
                                 is_all_executions_finished(
                                     self.client, self.deployment_id),
                                 timeout=self.timeout,
                                 expected_result=True):
            return ctx.operation.retry(
                'The "{0}" deployment is not ready for execution.'.format(
                    self.deployment_id))

        # we must to run some execution
        if not self.deployment.get(EXTERNAL_RESOURCE):

            # If the target deployment has the smart_update workflow defined,
            # execute it
            # If not, skip
            deployment_request_args = \
                dict(deployment_id=self.deployment_id)
            deployment = self._http_client_wrapper(
                'deployments', 'get', deployment_request_args)
            ctx.logger.debug('Get deployment response: {}'.format(
                deployment
            ))
            workflows_names_list = []
            for workflow in deployment.get('workflows'):
                workflows_names_list.append(workflow.get('name'))
            if 'smart_update' not in workflows_names_list:
                ctx.logger.debug(
                    """Target deployment doesn't support smart_update.
                    Skipping."""
                )
                return

            execution_args = self.config.get('executions_start_args', {})
            update_request_args = \
                dict(deployment_id=self.deployment_id,
                     **execution_args)

            deployment_updates = None
            task_retries = Component.get_task_retries_from_config()
            for retry in range(0, task_retries):
                try:
                    deployment_updates = self._http_client_wrapper(
                        'deployment_updates',
                        'update_with_existing_blueprint',
                        update_request_args)
                    break
                except NonRecoverableError:
                    if retry + 1 >= task_retries:
                        raise
                    else:
                        ctx.logger.debug(
                            'Deployment Update failed. Retry {}/{}'.format(
                                retry + 1, task_retries))

        ctx.logger.debug('Execution start response: "{0}".'.format(deployment_updates))

        execution_id = deployment_updates['execution_id']
        if not self.verify_execution_successful(execution_id):
            ctx.logger.error('Execution {0} failed for update of "{1}" '
                             'deployment'.format(execution_id,
                                                 self.deployment_id))

        ctx.logger.info('Execution succeeded for update of "{0}" deployment'.format(
            self.deployment_id))
        populate_runtime_with_wf_results(self.client, self.deployment_id)
        return True

    @staticmethod
    def get_task_retries_from_config():
        entry = next(x for x in ctx.get_config() if x.get('name') == TASK_RETRIES)
        value = entry.get('value')
        return int(value)
