# Copyright (c) 2015 Universidade Federal Fluminense (UFF)
# Copyright (c) 2015 Polytechnic Institute of New York University.
# This file is part of noWorkflow.
# Please, consult the license terms in the LICENSE file.

from __future__ import (absolute_import, print_function,
                        division, unicode_literals)

from collections import namedtuple, defaultdict, OrderedDict
from .structures import Single, Call, Group, Mixed
from ..utils import OrderedCounter


Edge = namedtuple("Edge", "node count")


class TreeVisitor(object):

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.delegated = {
            'initial': Edge(0, 1)
        }
        self.nid = 0
        self.min_duration = defaultdict(lambda: 1000^10)
        self.max_duration = defaultdict(lambda: 0)
        self.keep = None

    def update_durations(self, duration, tid):
        self.max_duration[tid] = max(self.max_duration[tid], duration)
        self.min_duration[tid] = min(self.min_duration[tid], duration)

    def update_node(self, node):
        node['mean'] = node['duration'] / node['count']
        node['info'].update_by_node(node)
        node['info'] = repr(node['info'])

    def to_dict(self):
        for node in self.nodes:
            n = node['node']
            self.update_node(n)
            self.update_durations(n['duration'], n['trial_id'])

        self.update_edges()
        return {
            'nodes': self.nodes,
            'edges': self.edges,
            'min_duration': self.min_duration,
            'max_duration': self.max_duration
        }

    def update_edges(self):
        pass

    def add_node(self, node):
        self.nodes.append(node.to_dict(self.nid))
        original = self.nid
        self.nid += 1
        return original

    def add_edge(self, source, target, count, typ):
        self.edges.append({
            'source': source,
            'target': target,
            'count': count,
            'type': typ
        })

    def visit_call(self, call):
        caller_id = self.add_node(call.caller)
        self.nodes[caller_id]['repr'] = repr(call)
        callees = call.called.visit(self)
        pos = 1
        for callee_id in callees:
            self.add_edge(caller_id, callee_id, pos, 'call')
            pos += 1
        return [caller_id]

    def visit_group(self, group):
        result = []
        for element in group.nodes.values():
            result += element.visit(self)
        return result

    def visit_single(self, single):
        return [self.add_node(single)]

    def visit_mixed(self, mixed):
        mixed.mix_results()
        node_id = mixed.first.visit(self)
        self.nodes[node_id[0]]['duration'] = mixed.duration
        return node_id


class NoMatchVisitor(TreeVisitor):

    def update_edges(self):
        for edge in self.edges:
            if edge['type'] in ['return', 'call']:
                edge['count'] = ''

    def use_delegated(self):
        result = self.delegated
        self.delegated = {}
        return result

    def solve_delegation(self, node_id, node_count, delegated):
        self.solve_cis_delegation(node_id, node_count, delegated)
        self.solve_ret_delegation(node_id, node_count, delegated)

    def solve_cis_delegation(self, node_id, node_count, delegated):
        # call initial sequence
        for typ in ['call', 'initial', 'sequence']:
            if typ in delegated:
                edge = delegated[typ]
                self.add_edge(edge.node, node_id, node_count, typ)

    def solve_ret_delegation(self, node_id, node_count, delegated):
        if 'return' in delegated:
            edge = delegated['return']
            self.add_edge(node_id, edge.node, edge.count, 'return')

    def visit_call(self, call):
        delegated = self.use_delegated()
        caller_id = self.add_node(call.caller)
        self.nodes[caller_id]['repr'] = repr(call)

        if delegated:
            self.solve_delegation(caller_id, 0, delegated)

        self.delegated['call'] = Edge(caller_id, 1)
        self.delegated['return'] = Edge(caller_id, 1)

        call.called.visit(self)
        return caller_id, call

    def visit_group(self, group):
        delegated = self.use_delegated()

        node_map = {}
        for element in group.nodes.values():
            node_id, node = element.visit(self)
            node_map[node] = node_id

        self.solve_cis_delegation(node_map[group.next], group.count, delegated)
        self.solve_ret_delegation(node_map[group.last], group.count, delegated)

        for previous, edges in group.edges.items():
            for next, count in edges.items():
                self.add_edge(node_map[previous], node_map[next],
                              count, 'sequence')

        return node_map[group.next], group.next

    def visit_single(self, single):
        delegated = self.use_delegated()
        node_id = self.add_node(single)
        self.nodes[node_id]['repr'] = repr(single)

        if delegated:
            self.solve_delegation(node_id, single.count, delegated)
        return node_id, single

    def visit_mixed(self, mixed):
        mixed.mix_results()
        node_id, node = mixed.first.visit(self)
        self.nodes[node_id]['duration'] = mixed.duration
        return node_id, node


class ExactMatchVisitor(NoMatchVisitor):

    def visit_single(self, single):
        s = Single(single.activation)
        s.level = single.level
        s.use_id = False
        return s

    def visit_mixed(self, mixed):
        mixed.use_id = False
        m = Mixed(mixed.elements[0].visit(self))
        for element in elements[1:]:
            m.add_element(element.visit(self))
        m.level = mixed.level
        return m

    def visit_group(self, group):
        nodes = group.nodes.keys()
        g = Group()
        g.use_id = False
        g.initialize(nodes[1].visit(self),nodes[0].visit(self))
        for element in nodes[2:]:
            g.add_subelement(element.visit(self))
        g.level = group.level
        return g

    def visit_call(self, call):
        caller = call.caller.visit(self)
        called = call.called.visit(self)
        c = Call(caller, called)
        c.use_id = False
        c.level = call.level
        return c


class CombineVisitor(NoMatchVisitor):

    def __init__(self):
        super(CombineVisitor, self).__init__()
        self.context = {}
        self.context_edges = {}
        self.namestack = []

    def update_edges(self):
        pass

    def namespace(self):
        return ' '.join(self.namestack)

    def update_namespace_node(self, node, single):
        node['count'] += single.count
        node['duration'] += single.duration
        node['info'].add_activation(single.activation)

    def add_node(self, single):
        self.namestack.append(single.name_id())
        namespace = self.namespace()
        self.namestack.pop()
        if namespace in self.context:
            context = self.context[namespace]
            self.update_namespace_node(context['node'], single)

            return self.context[namespace]['index']

        single.namespace = namespace
        result = super(CombineVisitor, self).add_node(single)
        self.context[namespace] = self.nodes[-1]
        return result

    def add_edge(self, source, target, count, typ):

        edge = "{} {} {}".format(source, target, typ)

        if not edge in self.context_edges:
            super(CombineVisitor, self).add_edge(source, target,
                                                           count, typ)
            self.context_edges[edge] = self.edges[-1]
        else:
            e = self.context_edges[edge]
            self.context_edges[edge]['count'] += count

    def visit_call(self, call):
        self.namestack.append(call.caller.name_id())
        result = super(CombineVisitor, self).visit_call(call)
        self.namestack.pop()
        return result

    def visit_mixed(self, mixed):
        node_id, node = None, None
        for element in mixed.elements:
            node_id, node = element.visit(self)
        return node_id, node


def sequence(previous, next):
    if isinstance(next, Group):
        next.add_subelement(previous)
        return next
    return Group().initialize(previous, next)


def list_to_call(stack):
    group = stack.pop()
    next = group.pop()
    while group:
        previous = group.pop()
        next = sequence(previous, next)
    caller = stack[-1].pop()
    call = Call(caller, next)
    call.level = caller.level
    next.level = caller.level + 1
    stack[-1].append(call)


def generate_graph(trial):
    """ Returns activation graph """
    activations = [Single(act) for act in trial.activations()]
    if not activations:
        return TreeElement(level=0)

    current = activations[0]
    stack = [[current]]
    level = OrderedDict()
    current.level = level[current.id] = 0

    for i in range(1, len(activations)):
        act = activations[i]
        act.level = level[act.id] = level[act.parent] + 1
        last = stack[-1][-1]
        if act.level == last.level:
            # act in the same level, add act to sequence
            stack[-1].append(act)
        elif act.level > last.level:
            # last called act
            stack.append([act])
        else:
            # act is in higher level than last
            # create a call for last group
            # add act to existing sequence
            list_to_call(stack)
            stack[-1].append(act)

    while len(stack) > 1:
        list_to_call(stack)

    return(stack[-1][-1])


class TrialGraph(object):

    def __init__(self, trial_id):
        self._graph = None
        self.trial_id = trial_id

    def graph(self, trial=None):
        if not trial:
            from ..models import Trial
            trial = Trial(self.trial_id)
        if self._graph == None:
            self._graph = generate_graph(trial)
        return self._graph

    def tree(self, trial=None):
        graph = self.graph(trial)
        visitor = TreeVisitor()
        graph.visit(visitor)
        return visitor.to_dict()

    def no_match(self, trial=None):
        graph = self.graph(trial)
        visitor = NoMatchVisitor()
        graph.visit(visitor)
        return visitor.to_dict()

    def exact_match(self, trial=None):
        graph = self.graph(trial)
        graph = graph.visit(ExactMatchVisitor())
        visitor = NoMatchVisitor()
        graph.visit(visitor)
        return visitor.to_dict()

    def combine(self, trial=None):
        graph = self.graph(trial)
        visitor = CombineVisitor()
        graph.visit(visitor)
        return visitor.to_dict()
