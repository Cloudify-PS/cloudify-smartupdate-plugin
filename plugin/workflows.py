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
from cloudify.manager import get_rest_client

from . import lifecycle
from constants import UPDATE_OPERATION,
    PREUPDATE_OPERATIONS,
    POSTUPDATE_OPERATIONS

@workflow
def smart_update(ctx,
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
           node_instances_to_reinstall=None,
           preupdate=False,
           update=True,
           postupdate=False):
    node_instances_to_reinstall = node_instances_to_reinstall or []
    to_preupdate = []
    to_update = []
    to_postupdate = []

    for node_instance_to_reinstall in node_instances_to_reinstall:
        remove_from_reinstall = False

        if  PREUPDATE_OPERATIONS in node_instance_to_reinstall.node.operations:
            remove_from_reinstall = True
            to_preupdate.append(node_instance_to_reinstall)

        if  UPDATE_OPERATION in node_instance_to_reinstall.node.operations:
            remove_from_reinstall = True
            to_update.append(node_instance_to_reinstall)

        if  POSTUPDATE_OPERATION in node_instance_to_reinstall.node.operations:
            remove_from_reinstall = True
            to_postupdate.append(node_instance_to_reinstall)

        if remove_from_reinstall:
            node_instances_to_reinstall.remove(node_instance_to_reinstall)

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
        if skip_install:
            return
        # Adding nodes or node instances should be based on modified instances
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

        _handle_plugin_after_update(ctx, modified_entity_ids['plugin'], 'add')

    def _uninstall():
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

        _handle_plugin_after_update(
            ctx, modified_entity_ids['plugin'], 'remove'
        )

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

    def _preupdate():
        if not preupdate:
            return
        lifecycle.execute_preupdate_unlink_relationships(
            graph=graph,
            # TODO: node_instances & modified_relationship_ids ??
            node_instances=set(to_preupdate),
            modified_relationship_ids=modified_entity_ids['relationship']
        )

        lifecycle.preupdate_node_instances(
            graph=graph,
            # TODO: node_instances & related_nodes ??
            node_instances=to_preupdate,
            ignore_failure=ignore_failure,
            related_nodes=set(to_preupdate)
        )

        _handle_plugin_after_update(
            ctx, modified_entity_ids['plugin'], 'remove'
        )

    def _update():
        if not update:
            return
        # TODO: execute_operation(update)

    def _postupdate():
        if not postupdate:
            return
        # Adding nodes or node instances should be based on modified instances
        lifecycle.install_node_instances(
            graph=graph,
            # TODO: node_instances & related_nodes ??
            node_instances=to_postupdate,
            related_nodes=set(to_postupdate)
        )

        # This one as well.
        lifecycle.execute_establish_relationships(
            graph=graph,
            # TODO: node_instances & modified_relationship_ids ??
            node_instances=set(to_postupdate),
            modified_relationship_ids=modified_entity_ids['relationship']
        )

        _handle_plugin_after_update(ctx, modified_entity_ids['plugin'], 'add')

    _uninstall()
    _preupdate()
    _update()
    _reinstall()
    _postupdate()
    _install()

    # Finalize the commit (i.e. remove relationships or nodes)
    if update_id is not None:
        client = get_rest_client()
        client.deployment_updates.finalize_commit(update_id)

def _handle_plugin_after_update(ctx, plugins_list, action):
    """ Either install or uninstall plugins on the relevant hosts """

    prefix = 'I' if action == 'add' else 'Uni'
    message = '{0}nstalling plugins'.format(prefix)

    graph = ctx.graph_mode()
    plugin_subgraph = graph.subgraph('handle_plugins')

    # The plugin_list is a list of (possibly empty) dicts that may contain
    # `add`/`remove` keys and (node_id, plugin_dict) values. E.g.
    # [{}, {}, {'add': (NODE_ID, PLUGIN_DICT)},
    # {'add': (NODE_ID, PLUGIN_DICT), 'remove': (NODE_ID, PLUGIN_DICT)}]
    # So we filter out only those dicts that have the relevant action
    plugins_to_handle = [p[action] for p in plugins_list if p.get(action)]

    # The list might contain duplicates, and it's organized in the following
    # way: [(node_id, plugin_dict), (node_id, plugin_to_handle), ...] so
    # we reorganize it into: {node_id: [list_of_plugins], ...}
    node_to_plugins_map = {}
    for node, plugin in plugins_to_handle:
        node_list = node_to_plugins_map.setdefault(node, [])
        if plugin not in node_list:
            node_list.append(plugin)

    for node_id, plugins in node_to_plugins_map.items():
        if not plugins:
            continue

        instances = ctx.get_node(node_id).instances
        for instance in instances:
            if action == 'add':
                task = lifecycle.plugins_install_task(instance, plugins)
            else:
                task = lifecycle.plugins_uninstall_task(instance, plugins)

            if task:
                seq = plugin_subgraph.sequence()
                seq.add(
                    instance.send_event(message),
                    task
                )
    graph.execute()
