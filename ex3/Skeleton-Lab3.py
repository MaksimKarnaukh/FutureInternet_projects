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

class CustomSlice (EventMixin):
	def __init__(self):
		self.listenTo(core.openflow)
		core.openflow_discovery.addListeners(self)

		# Adjacency map.  [sw1][sw2] -> port from sw1 to sw2
		self.adjacency = defaultdict(lambda:defaultdict(lambda:None))

		'''
		We suggest an structure that relates origin-destination MAC address and port:
		(dpid, origin MAC, destination MAC, port : following dpid)
		The structure of self.portmap is a four-tuple key and a string value.
		The type is:
		(dpid string, src MAC addr, dst MAC addr, port (int)) -> dpid of next switch
		'''

		self.portmap = {
			# Video Traffic (Port 200, UDP) - High Bandwidth (100 Mbps Links)
			# h1 -> Video Server
			('00-00-00-00-00-01', EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:05'), 200): '00-00-00-00-00-04',
			('00-00-00-00-00-04', EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:05'), 200): '00-00-00-00-00-07',

			# h4 -> Video Server
			('00-00-00-00-00-03', EthAddr('00:00:00:00:00:04'), EthAddr('00:00:00:00:00:05'), 200): '00-00-00-00-00-02',
			('00-00-00-00-00-02', EthAddr('00:00:00:00:00:04'), EthAddr('00:00:00:00:00:05'), 200): '00-00-00-00-00-01',
			('00-00-00-00-00-01', EthAddr('00:00:00:00:00:04'), EthAddr('00:00:00:00:00:05'), 200): '00-00-00-00-00-04',
			('00-00-00-00-00-04', EthAddr('00:00:00:00:00:04'), EthAddr('00:00:00:00:00:05'), 200): '00-00-00-00-00-07',

			# HTTP Traffic (Port 80, TCP) - Low Bandwidth (10 Mbps Links)
			# h1 -> HTTP Server
			('00-00-00-00-00-01', EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-02',
			('00-00-00-00-00-02', EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-05',
			('00-00-00-00-00-05', EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-07',

			# h2 -> HTTP Server
			('00-00-00-00-00-02', EthAddr('00:00:00:00:00:02'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-05',
			('00-00-00-00-00-05', EthAddr('00:00:00:00:00:02'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-07',

			# h3 -> HTTP Server
			('00-00-00-00-00-03', EthAddr('00:00:00:00:00:03'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-06',
			('00-00-00-00-00-06', EthAddr('00:00:00:00:00:03'), EthAddr('00:00:00:00:00:06'), 80): '00-00-00-00-00-07',
		}

		# (dpid string, dst MAC addr) -> port (int)
		self.switch_to_hosts_ports = {
			('00-00-00-00-00-01', EthAddr('00:00:00:00:00:01')): 1,
			('00-00-00-00-00-02', EthAddr('00:00:00:00:00:02')): 2,
			('00-00-00-00-00-03', EthAddr('00:00:00:00:00:03')): 2,
			('00-00-00-00-00-03', EthAddr('00:00:00:00:00:04')): 3,
			('00-00-00-00-00-07', EthAddr('00:00:00:00:00:05')): 4,
			('00-00-00-00-00-07', EthAddr('00:00:00:00:00:06')): 5,
		}

	def _handle_ConnectionUp(self, event):
		dpid = dpidToStr(event.dpid)
		log.debug("Switch %s has connected.", dpid)

	def _handle_LinkEvent (self, event):
		l = event.link
		sw1 = dpid_to_str(l.dpid1)
		sw2 = dpid_to_str(l.dpid2)
		log.debug ("link %s[%d] <-> %s[%d]",
			sw1, l.port1,
			sw2, l.port2)
		self.adjacency[sw1][sw2] = l.port1
		self.adjacency[sw2][sw1] = l.port2

	def _handle_PacketIn (self, event):
		"""
		Handle packet in messages from the switch to implement above algorithm.
		"""
		packet = event.parsed
		tcpp = event.parsed.find('tcp')
		udpp = event.parsed.find('udp')
		'''tcpp=80'''

		# flood, but don't install the rule
		def flood (message = None):
			""" Floods the packet """
			msg = of.ofp_packet_out()
			msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
			msg.data = event.ofp
			msg.in_port = event.port
			event.connection.send(msg)

		def install_fwdrule(event,packet,outport):
			msg = of.ofp_flow_mod()
			msg.idle_timeout = 10
			msg.hard_timeout = 30
			msg.match = of.ofp_match.from_packet(packet, event.port)
			msg.actions.append(of.ofp_action_output(port = outport))
			msg.data = event.ofp
			msg.in_port = event.port
			event.connection.send(msg)

		
		def forward (message = None):
			this_dpid = dpid_to_str(event.dpid)

			print("Packet received from %s at %s (port %d)" % (packet.src, this_dpid, event.port))

			if packet.dst.is_multicast:
				flood()
				return
			else:
				log.debug("Got unicast packet for %s at %s (input port %d):",
					packet.dst, dpid_to_str(event.dpid), event.port)

				try:
					""" Add your logic here """

					if udpp and udpp.dstport == 200:  # Video Service
						log.debug("Video traffic detected: %s -> %s", packet.src, packet.dst)
						path_key = (this_dpid, packet.src, packet.dst, 200)
					elif tcpp and tcpp.dstport == 80:  # HTTP Service
						log.debug("HTTP traffic detected: %s -> %s", packet.src, packet.dst)
						path_key = (this_dpid, packet.src, packet.dst, 80)
					else:
						flood()
						return

					try:
						next_hop_dpid = self.portmap[path_key]
						outport = self.adjacency[this_dpid][next_hop_dpid]

						log.debug("Forwarding to next hop: %s via port %d", next_hop_dpid, outport)
						install_fwdrule(event, packet, outport)

					except KeyError:
						outport = self.switch_to_hosts_ports[(this_dpid, packet.dst)]
						log.debug("Forwarding to host %s via port %d", packet.dst, outport)
						install_fwdrule(event, packet, outport)

				except AttributeError:
					log.debug("packet type has no transport ports, flooding")
					# flood and install the flow table entry for the flood
					install_fwdrule(event,packet,of.OFPP_FLOOD)

		forward()

def launch():
	# Ejecute spanning tree para evitar problemas con topologías con bucles
	pox.openflow.discovery.launch()
	pox.openflow.spanning_tree.launch()

	core.registerNew(CustomSlice)

