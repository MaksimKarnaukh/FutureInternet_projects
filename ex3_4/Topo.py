from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost, RemoteController
from mininet.link import TCLink
from mininet.util import irange,dumpNodeConnections
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.nodelib import LinuxBridge
from mininet.node import OVSSwitch
from mininet.node import OVSKernelSwitch, UserSwitch
import random

class P32( Topo ):
    def __init__(self):
        # Initialize topology and default options
        Topo.__init__(self)
        linkopts1 = {'bw':1}
        linkopts2 = {'bw':10}
        linkopts3 = {'bw':100}
        linkopts = [linkopts1, linkopts2, linkopts3]
        
        switches = {}
        hosts = {}
        
        for i in range(1,8):
            sconfig = {'dpid': "%016x" % (i)}
            sn = self.addSwitch('s%s' % i,**sconfig)
            if i<7:
                Host = self.addHost( 'h%s' % i, ip="10.0.0.%s/24" %i, mac="00:00:00:00:00:0%s" %i )
                hosts['h%s' % i] = Host
            switches['s%s' % i] = sn
            

		#S1
        self.addLink('s1','h1', **linkopts[2])
        self.addLink('s1','s2', **linkopts[2])
        self.addLink('s1','s4', **linkopts[2])

  
  		#S2
        self.addLink('s2','h2', **linkopts[2])
        self.addLink('s2','s3', **linkopts[2])
        self.addLink('s2','s5', **linkopts[1])

  
  		#S3
        self.addLink('s3','h3', **linkopts[2])
        self.addLink('s3','h4', **linkopts[2])
        self.addLink('s3','s6', **linkopts[1])

  		#S4
        self.addLink('s4','s5', **linkopts[2])
        self.addLink('s4','s7', **linkopts[2])
  
  		#S5
        self.addLink('s5','s6', **linkopts[1])
        self.addLink('s5','s7', **linkopts[1])

  		#S6
        self.addLink('s6','s7', **linkopts[1])
  
  		#S7
        self.addLink('s7','h5', **linkopts[2])
        self.addLink('s7','h6', **linkopts[2])

class P31( Topo ):
    "Simple topology example."
    def __init__(self):
        # Initialize topology and default options
        Topo.__init__(self)
        linkopts1 = {'bw':10}
        linkopts2 = {'bw':100}
        linkopts3 = {'bw':1000}
        linkopts = [linkopts1, linkopts2, linkopts3]
        
        switches = {}
        hosts = {}
        for i in range(1,5):
            sconfig = {'dpid': "%016x" % (i)}
            sn = self.addSwitch('s%s' % i,**sconfig)
            Host = self.addHost( 'h%s' % i, ip="10.0.0.%s/24" %i, mac="00:00:00:00:00:0%s" %i )
            switches['s%s' % i] = sn
            hosts['h%s' % i] = Host
        

        self.addLink('s1','s2',port1=1, port2=1,**linkopts[1])
        self.addLink('s2','s3',port1=2, port2=1,**linkopts[1])
        self.addLink('s1','s4',port1=2, port2=1,**linkopts[0])
        self.addLink('s3','s4',port1=2, port2=2,**linkopts[0])
        self.addLink('s1','h1',port1=3, port2=1,**linkopts[1])
        self.addLink('s1','h2',port1=4, port2=1,**linkopts[1])
        self.addLink('s3','h3',port1=3, port2=1,**linkopts[1])
        self.addLink('s3','h4',port1=4, port2=1,**linkopts[1])
        
        
class RandomTopo( Topo ):
    "Simple topology example."
    def __init__(self, N = 5):
        # Initialize topology and default options
        Topo.__init__(self)
        linkopts1 = {'bw':10, 'delay':'1ms', 'loss':0.1, 'max_queue_size':1000, 'use_htb':True}
        linkopts2 = {'bw':100, 'delay':'10ms', 'loss':0.1, 'max_queue_size':1000, 'use_htb':True}
        linkopts3 = {'bw':1000, 'delay':'50ms', 'loss':0.1, 'max_queue_size':1000, 'use_htb':True}
        linkopts = [linkopts1, linkopts2, linkopts3]
        #N = 6
        n = list(range(1,(N+1)))
        init_node = random.choice(n) #Beginning node
        link_count = random.randrange(N-1,(N*N-N)/2) #Number of links
        links = {} #List of created links
        av_links = {}
        for i in range(1,(N+1)):
            av_links[i] = list(range(1,(N+1)))
            av_links[i].remove(i)
            links[i] = []
        
        edges = []
        links_opt = []
        
        
        while len(n) > 1: #Generate at least a connected graph
            n.remove(init_node)
            end_node = random.choice(n)
            lo = random.choice(linkopts)
            links[end_node] = links[end_node] + [init_node,lo]
            av_links[end_node].remove(init_node)
            links[init_node] = links[init_node] + [end_node,lo]
            av_links[init_node].remove(end_node)
            e = (init_node,end_node)
            edges.append(e)
            links_opt.append(lo)
            init_node = end_node
        
        
        for j in range(1,link_count-(N-2)):
            av_node = list(range(1,N+1))
            f_links_node = []
            for k in  range(1,N):
                if not av_links[k]:
                    av_node.remove(k)
            init_node = random.choice(av_node)
            av_node.remove(init_node)
            lo = random.choice(linkopts)
            end_node = random.choice(av_links[init_node])
            links[end_node] = links[end_node] + [init_node,lo]
            av_links[end_node].remove(init_node)
            links[init_node] = links[init_node] + [end_node,lo]
            av_links[init_node].remove(end_node)
            e = (init_node,end_node)
            edges.append(e)
            links_opt.append(lo)
        
        
        switches = []
        for i in range(1,(N+1)):
            sn = self.addSwitch('s%s' % i)
            Host = self.addHost( 'h%s' % i, ip="10.0.0.%s/24" %i, mac="00:00:00:00:00:0%s" %i )
            self.addLink(sn,Host)
            switches.append(sn)
            
        for i in range(0,len(edges)):
            self.addLink(switches[edges[i][0]-1],switches[edges[i][1]-1],**links_opt[i])
            

class P41( Topo ):
    "Simple topology example."
    def __init__(self):
        # Initialize topology and default options
        Topo.__init__(self)
        linkopts1 = {'bw':10}
        linkopts2 = {'bw':100}
        linkopts3 = {'bw':1000}
        linkopts = [linkopts1, linkopts2, linkopts3]
        
        switches = []
        hosts = []
        for i in range(1,7):
            sn = self.addSwitch('s%s' % i)
            Host = self.addHost( 'h%s' % i, ip="10.0.0.%s/24" %i, mac="00:00:00:00:00:0%s" %i )
            self.addLink(sn,Host,**linkopts[2])
            switches.append(sn)
            hosts.append(Host)
        
        self.addLink(switches[0],switches[1],**linkopts[1])
        self.addLink(switches[0],switches[5],**linkopts[0])
        self.addLink(switches[0],switches[3],**linkopts[2])
        self.addLink(switches[2],switches[1],**linkopts[1])
        self.addLink(switches[2],switches[5],**linkopts[1])
        self.addLink(switches[4],switches[3],**linkopts[2])
        self.addLink(switches[4],switches[5],**linkopts[2])

topos = { 'p3-2':  P32, 'p3-1': P31, 'p4-1': P41, 'p4-2':RandomTopo }

