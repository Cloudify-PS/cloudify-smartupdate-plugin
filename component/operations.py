# Copyright (c) 2017-2019 Cloudify Platform Ltd. All rights reserved
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

from cloudify.decorators import operation

from cloudify_types.utils import proxy_operation

from .component import Component


@operation(resumable=True)
@proxy_operation('upload_blueprint')
def upload_blueprint(operation, **_):
    return getattr(Component(_), operation)()


@operation(resumable=True)
@proxy_operation('create_deployment')
def create(operation, **_):
    return getattr(Component(_), operation)()


@operation(resumable=True)
@proxy_operation('delete_deployment')
def delete(operation, **_):
    return getattr(Component(_), operation)()


@operation(resumable=True)
@proxy_operation('execute_workflow')
def execute_start(operation, **_):
    return getattr(Component(_), operation)()


@operation(resumable=True)
@proxy_operation('prepare_deployment_update')
def prepare_deployment_update(operation, **_):
    return getattr(Component(_), operation)()


@operation(resumable=True)
@proxy_operation('execute_deployment_update')
def execute_deployment_update(operation, **_):
    return getattr(Component(_), operation)()


@operation(resumable=True)
@proxy_operation('cleanup_deployment_update')
def cleanup_deployment_update(operation, **_):
    return getattr(Component(_), operation)()
