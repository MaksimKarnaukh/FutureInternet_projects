'''
Coursera:
- Software Defined Networking (SDN) course
-- Network Virtualization

Professor: Nick Feamster
Teaching Assistant: Arpit Gupta
'''

from pox.core import core
from collections import defaultdict

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_tree

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
from collections import namedtuple
import os

log = core.getLogger()


class TopologySlice (EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        log.debug("Enabling Slicing Module")


    def add_flow_rule(self, connection, in_port, out_port, bidirectional=True):
        """
        Adds a flow rule to the switch.

        :param connection: connection.
        :param in_port: The incoming port to match traffic.
        :param out_port: The outgoing port to forward traffic.
        :param bidirectional: If True, a rule will be added in both directions.
        """
        msg = of.ofp_flow_mod()
        msg.match.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        connection.send(msg)

        if bidirectional:
            msg = of.ofp_flow_mod()
            msg.match.in_port = out_port
            msg.actions.append(of.ofp_action_output(port=in_port))
            connection.send(msg)
        
        
    """This event will be raised each time a switch will connect to the controller"""
    def _handle_ConnectionUp(self, event):
        
        # Use dpid to differentiate between switches (datapath-id)
        # Each switch has its own flow table. As we'll see in this 
        # example we need to write different rules in different tables.
        dpid = dpidToStr(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        
        """ Add your logic here """

        topo = {'00-00-00-00-00-01': [[3, 1], [4, 2]],
                '00-00-00-00-00-02': [[1,2]],
                '00-00-00-00-00-03': [[1, 3], [2, 4]],
                '00-00-00-00-00-04': [1,2]}

        for path in topo[dpid]:
            self.add_flow_rule(event.connection, path[0], path[1])


def launch():
    # Run spanning tree so that we can deal with topologies with loops
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    '''
    Starting the Topology Slicing module
    '''
    core.registerNew(TopologySlice)
