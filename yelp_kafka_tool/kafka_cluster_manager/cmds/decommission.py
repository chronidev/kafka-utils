from __future__ import print_function

import logging
import sys

from .command import ClusterManagerCmd
from yelp_kafka_tool.kafka_cluster_manager. \
    cluster_info.util import validate_plan
from yelp_kafka_tool.kafka_cluster_manager.util import assignment_to_plan


DEFAULT_MAX_PARTITION_MOVEMENTS = 1
DEFAULT_MAX_LEADER_CHANGES = 5


class DecommissionCmd(ClusterManagerCmd):

    def __init__(self):
        super(DecommissionCmd, self).__init__()
        self.log = logging.getLogger(self.__class__.__name__)

    def build_subparser(self, subparsers):
        subparser = subparsers.add_parser(
            'decommission',
            description='Decommission one or more brokers of the cluster.',
            help='This command is used to move all the replicas assigned to given '
            'brokers and redistribute them across all the other brokers while '
            'trying to keep the cluster balanced.',
        )
        subparser.add_argument(
            'broker_ids',
            nargs='+',
            type=int,
            help='Broker ids of the brokers to decommission.',
        )
        subparser.add_argument(
            '--max-partition-movements',
            type=self.positive_int,
            default=DEFAULT_MAX_PARTITION_MOVEMENTS,
            help='Maximum number of partition-movements in final set of actions.'
                 ' DEFAULT: %(default)s. RECOMMENDATION: Should be at least max '
                 'replication-factor across the cluster.',
        )
        subparser.add_argument(
            '--max-leader-changes',
            type=self.positive_int,
            default=DEFAULT_MAX_LEADER_CHANGES,
            help='Maximum number of actions with leader-only changes.'
                 ' DEFAULT: %(default)s',
        )
        return subparser

    def run_command(self, cluster_topology):
        base_assignment = cluster_topology.assignment
        cluster_topology.decommission_brokers(self.args.broker_ids)

        if not validate_plan(
            assignment_to_plan(cluster_topology.assignment),
            assignment_to_plan(base_assignment),
        ):
            self.log.error('Invalid assignment %s.', cluster_topology.assignment)
            print(
                'Invalid assignment: {0}'.format(cluster_topology.assignment),
                file=sys.stderr,
            )
            sys.exit(1)

        # Reduce the proposed assignment based on max_partition_movements
        # and max_leader_changes
        reduced_assignment = self.get_reduced_assignment(
            base_assignment,
            cluster_topology.assignment,
            self.args.max_partition_movements,
            self.args.max_leader_changes,
        )
        if reduced_assignment:
            self.process_assignment(reduced_assignment)
        else:
            self.log.info(
                "Cluster already balanced. No more replicas in "
                "decommissioned brokers."
            )
            print(
                "Cluster already balanced. No more replicas in "
                "decommissioned brokers."
            )
