########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

PREUPDATE_INTERFACE = 'cloudify.interfaces.preupdate'
UPDATE_INTERFACE = 'cloudify.interfaces.update'
POSTUPDATE_INTERFACE = 'cloudify.interfaces.postupdate'
PREUPDATE_RELATIONSHIP_INTERFACE = 'cloudify.interfaces.relationship_preupdate'
UPDATE_RELATIONSHIP_INTERFACE = 'cloudify.interfaces.relationship_update'
POSTUPDATE_RELATIONSHIP_INTERFACE = 'cloudify.interfaces.relationship_postupdate'

PREUPDATE_OPERATIONS = [
    PREUPDATE_INTERFACE + '.stop',
    PREUPDATE_INTERFACE + '.delete'
]
UPDATE_OPERATION = UPDATE_INTERFACE + '.update'
POSTUPDATE_OPERATIONS = [
    POSTUPDATE_INTERFACE + '.create',
    POSTUPDATE_INTERFACE + '.configure',
    POSTUPDATE_INTERFACE + '.start'
]
PREUPDATE_RELATIONSHIP_OPERATION = PREUPDATE_RELATIONSHIP_INTERFACE + '.unlink'
UPDATE_RELATIONSHIP_OPERATION = UPDATE_RELATIONSHIP_INTERFACE + '.update'
POSTUPDATE_RELATIONSHIP_OPERATIONS = [
    POSTUPDATE_RELATIONSHIP_INTERFACE + '.preconfigure',
    POSTUPDATE_RELATIONSHIP_INTERFACE + '.postconfigure',
    POSTUPDATE_RELATIONSHIP_INTERFACE + '.establish'
]
