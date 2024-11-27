#Part of this code is taken from the SDN coursera course by Prof. Nick Feamster


from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.addresses import EthAddr
from collections import namedtuple
import os

import csv

#Please add the classes and methods you consider necessary



log = core.getLogger()
policyFile = "%s/pox/pox/misc/firewall-policies.csv" % os.environ[ 'HOME' ]  




class Firewall(EventMixin):

    def __init__ (self):
        self.listenTo(core.openflow)
        log.debug("Activating Firewall")

        self.blocked_mac_pairs = []

        self.load_policies()

    def load_policies(self):

        try:
            with open(policyFile, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mac_0 = EthAddr(row['mac_0'])
                    mac_1 = EthAddr(row['mac_1'])
                    self.blocked_mac_pairs.append((mac_0, mac_1))
                    log.debug("Blocking traffic between %s and %s", mac_0, mac_1)

        except Exception as e:
            log.error("Error loading firewall policies: %s", e)

    def _handle_ConnectionUp(self, event):

        #Please add your code here

        for mac_0, mac_1 in self.blocked_pairs:
            msg = of.ofp_flow_mod()
            msg.match.dl_src = mac_0
            msg.match.dl_dst = mac_1
            msg.actions = []
            event.connection.send(msg)

            msg = of.ofp_flow_mod()
            msg.match.dl_src = mac_1
            msg.match.dl_dst = mac_0
            msg.actions = []
            event.connection.send(msg)
    
        log.debug("Installed rules in %s", dpidToStr(event.dpid))

def launch ():

    core.registerNew(Firewall)
