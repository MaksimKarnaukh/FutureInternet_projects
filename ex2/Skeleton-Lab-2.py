#Part of this code is taken from the SDN coursera course by Prof. Nick Feamster


from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.addresses import EthAddr
from collections import namedtuple
import os

#Please add the classes and methods you consider necessary



log = core.getLogger()
policyFile = "%s/pox/pox/misc/firewall-policies.csv" % os.environ[ 'HOME' ]  




class Firewall(EventMixin):

    def __init__ (self):
        self.listenTo(core.openflow)
        log.debug("Activating Firewall")

    def _handle_ConnectionUp (self, event):    
         #Please add your code here
    
        log.debug("Installed rules in %s", dpidToStr(event.dpid))

def launch ():

    core.registerNew(Firewall)
