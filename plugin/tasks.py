########
# Copyright (c) 2020 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.
from cloudify import ctx
from cloudify.decorators import operation
from cloudify.constants import RELATIONSHIP_INSTANCE, NODE_INSTANCE

@operation
def get_operation_name(**kwargs):
    if ctx.type == RELATIONSHIP_INSTANCE:
        ctx.logger.debug('Executing {} on source {} & target {}'.format(
            ctx.operation.name,
            ctx.source.node.name,
            ctx.target.node.name))
    elif ctx.type == NODE_INSTANCE:
        ctx.logger.debug('Executing {} on {}'.format(
            ctx.operation.name, ctx.node.name))
