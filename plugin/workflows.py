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


# ctx is imported and used in operations

from cloudify.decorators import workflow
from cloudify.plugins import lifecycle
from cloudify.manager import get_rest_client
from cloudify.utils import add_plugins_to_install, add_plugins_to_uninstall
from cloudify.plugins.workflows import _handle_plugin_after_update

@workflow
def update(ctx,
           update_id,
           added_instance_ids,
           added_target_instances_ids,
           removed_instance_ids,
           remove_target_instance_ids,
           modified_entity_ids,
           extended_instance_ids,
           extend_target_instance_ids,
           reduced_instance_ids,
           reduce_target_instance_ids,
           skip_install,
           skip_uninstall,
           ignore_failure=False,
           install_first=False,
           node_instances_to_reinstall=None,
           central_plugins_to_install=None,
           central_plugins_to_uninstall=None,
           update_plugins=True):
    node_instances_to_reinstall = node_instances_to_reinstall or []
    instances_by_change = {
        'added_instances': (added_instance_ids, []),
        'added_target_instances_ids': (added_target_instances_ids, []),
        'removed_instances': (removed_instance_ids, []),
        'remove_target_instance_ids': (remove_target_instance_ids, []),
        'extended_and_target_instances':
            (extended_instance_ids + extend_target_instance_ids, []),
        'reduced_and_target_instances':
            (reduced_instance_ids + reduce_target_instance_ids, []),
    }
    for instance in ctx.node_instances:
        instance_holders = [instance_holder
                            for _, (changed_ids, instance_holder)
                            in instances_by_change.iteritems()
                            if instance.id in changed_ids]
        for instance_holder in instance_holders:
            instance_holder.append(instance)

    graph = ctx.graph_mode()
    to_install = set(instances_by_change['added_instances'][1])
    to_uninstall = set(instances_by_change['removed_instances'][1])

    def _install():
        def _install_nodes():
            if skip_install:
                return
            # Adding nodes or node instances should be based on modified
            # instances
            lifecycle.install_node_instances(
                graph=graph,
                node_instances=to_install,
                related_nodes=set(
                    instances_by_change['added_target_instances_ids'][1])
            )

            # This one as well.
            lifecycle.execute_establish_relationships(
                graph=graph,
                node_instances=set(
                    instances_by_change['extended_and_target_instances'][1]),
                modified_relationship_ids=modified_entity_ids['relationship']
            )

        _install_nodes()
        _install_plugins_on_agent()

    def _uninstall():
        def _uninstall_nodes():
            if skip_uninstall:
                return
            lifecycle.execute_unlink_relationships(
                graph=graph,
                node_instances=set(
                    instances_by_change['reduced_and_target_instances'][1]),
                modified_relationship_ids=modified_entity_ids['relationship']
            )

            lifecycle.uninstall_node_instances(
                graph=graph,
                node_instances=to_uninstall,
                ignore_failure=ignore_failure,
                related_nodes=set(
                    instances_by_change['remove_target_instance_ids'][1])
            )

        _uninstall_nodes()
        _uninstall_plugins_on_agent()

    def _reinstall():
        subgraph = set([])
        for node_instance_id in node_instances_to_reinstall:
            subgraph |= ctx.get_node_instance(
                node_instance_id).get_contained_subgraph()
        subgraph -= to_uninstall
        intact_nodes = set(ctx.node_instances) - subgraph - to_uninstall
        for n in subgraph:
            for r in n._relationship_instances:
                if r in removed_instance_ids:
                    n._relationship_instances.pop(r)
        lifecycle.reinstall_node_instances(graph=graph,
                                           node_instances=subgraph,
                                           related_nodes=intact_nodes,
                                           ignore_failure=ignore_failure)

    def _uninstall_plugins_on_agent():
        if not update_plugins:
            return
        _handle_plugin_after_update(
            ctx, modified_entity_ids['plugin'], 'remove')

    def _install_plugins_on_agent():
        if not update_plugins:
            return
        _handle_plugin_after_update(
            ctx, modified_entity_ids['plugin'], 'add')

    def _update_central_plugins():
        if not update_plugins:
            return
        sequence = graph.sequence()
        add_plugins_to_uninstall(ctx, central_plugins_to_uninstall, sequence)
        add_plugins_to_install(ctx, central_plugins_to_install, sequence)
        graph.execute()

    if install_first:
        _install()
        _uninstall()
    else:
        _uninstall()
        _install()
    _reinstall()

    _update_central_plugins()

    # Finalize the commit (i.e. remove relationships or nodes)
    client = get_rest_client()
    client.deployment_updates.finalize_commit(update_id)


