'''
Assignment in class
'''

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange,dumpNodeConnections
from mininet.log import setLogLevel

class CustomTopo(Topo):
    "Simple Data Center Topology"

    "linkopts - (1:core, 2:aggregation, 3: edge) parameters"
    "fanout - number of child switch per parent switch"
    def __init__(self, linkopts1, linkopts2, linkopts3, fanout=2, **opts):
        # Initialize topology and default options
        Topo.__init__(self, **opts)

        host_counter = 1

        # Core switch
        core = self.addSwitch('s1')
        # Aggregation switches
        for i in irange(1, fanout):
            agg = self.addSwitch('s2%s' % i)
            self.addLink(agg, core, **linkopts1)
            # Edge switches
            for j in irange(1, fanout):
                edge = self.addSwitch('s3%s%s' % (i, j))
                self.addLink(edge, agg, **linkopts2)
                # Hosts
                for k in irange(1, fanout):

                    # host = self.addHost('h%s%s%s' % (i, j, k))
                    host = self.addHost('h%s' % host_counter) # for perfTest code, we need to have host name as h1, h2, h3, etc
                    self.addLink(host, edge, **linkopts3)
                    host_counter += 1
        
                    
def perfTest():
    "Create network and run simple performance test"
    linkopts1 = {'bw':10, 'delay':'50ms', 'loss':0.1, 'max_queue_size':1000, 'use_htb':True}
    linkopts2 = {'bw':100, 'delay':'10ms', 'loss':0.1, 'max_queue_size':1000, 'use_htb':True}
    linkopts3 = {'bw':1000, 'delay':'1ms', 'loss':0.1, 'max_queue_size':1000, 'use_htb':True}
    topo = CustomTopo(linkopts1,linkopts2,linkopts3,fanout=3)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink)
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    print "Testing network connectivity"
    net.pingAll()
    print "Testing bandwidth between h1 and h2"
    h1, h2 = net.get('h1', 'h2')
    net.iperf((h1, h2))
    print "Testing bandwidth between h1 and h2"
    h1, h4 = net.get('h1', 'h4')
    net.iperf((h1, h4))
    print "Testing bandwidth between h1 and h6"
    h1, h6 = net.get('h1', 'h6')
    net.iperf((h1, h6))
    net.stop()


if __name__ == '__main__':
   setLogLevel('info')
   perfTest()
