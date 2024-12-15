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

	def add_portmap_entry(self, src_dpid, src_mac, dst_mac, port, dst_dpid, bidirectional=True):
		"""
		Adds an entry to the portmap.
		:param src_dpid: source switch dpid string
		:param src_mac: source MAC address
		:param dst_mac: destination MAC address
		:param port: port number
		:param dst_dpid: destination switch dpid string
		:param bidirectional: if True, the entry will be added in both directions
		"""
		self.portmap[(src_dpid, src_mac, dst_mac, port)] = dst_dpid
		if bidirectional:
			self.portmap[(dst_dpid, dst_mac, src_mac, port)] = src_dpid

	def add_portmap_path(self, src_mac, dst_mac, port, path, bidirectional=True):
		"""
		Adds a path to the portmap. A path is a list of consecutive switch dpid strings.
		:param src_mac: source MAC address
		:param dst_mac: destination MAC address
		:param port: port number
		:param path: list of switch dpid strings
		:param bidirectional: if True, the path will be added in both directions
		"""
		for i in range(len(path) - 1):
			self.add_portmap_entry(src_dpid=path[i], src_mac=src_mac, dst_mac=dst_mac, port=port, dst_dpid=path[i + 1],
							  bidirectional=bidirectional)

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

		self.portmap = {}
		self.add_portmap_path(EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:05'), 200, ['00-00-00-00-00-01', '00-00-00-00-00-04', '00-00-00-00-00-07'])
		self.add_portmap_path(EthAddr('00:00:00:00:00:04'), EthAddr('00:00:00:00:00:05'), 200, ['00-00-00-00-00-03', '00-00-00-00-00-02', '00-00-00-00-00-01', '00-00-00-00-00-04', '00-00-00-00-00-07'])
		self.add_portmap_path(EthAddr('00:00:00:00:00:01'), EthAddr('00:00:00:00:00:06'), 80, ['00-00-00-00-00-01', '00-00-00-00-00-02', '00-00-00-00-00-05', '00-00-00-00-00-07'])
		self.add_portmap_path(EthAddr('00:00:00:00:00:02'), EthAddr('00:00:00:00:00:06'), 80, ['00-00-00-00-00-02', '00-00-00-00-00-05', '00-00-00-00-00-07'])
		self.add_portmap_path(EthAddr('00:00:00:00:00:03'), EthAddr('00:00:00:00:00:06'), 80, ['00-00-00-00-00-03', '00-00-00-00-00-06', '00-00-00-00-00-07'])

		print(len(self.portmap), self.portmap)

		'''
		self.switch_to_hosts_ports is a dictionary that relates switch dpid and host MAC address to port:
		(dpid string, dst MAC addr) -> port (int)
		'''
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

			if packet.dst.is_multicast:
				flood()
				return

			log.debug("Got unicast packet for %s at %s (input port %d):", packet.dst, dpid_to_str(event.dpid), event.port)

			try:
				""" Add your logic here """

				log.debug("--------------------Start Forwarding--------------------")

				path_key = None
				if udpp:
					if udpp.dstport == 200: # Video Service
						log.debug("Video directed traffic detected: %s -> %s", packet.src, packet.dst)
					else:
						log.debug("UDP traffic detected: %s -> %s (Port: %d)", packet.src, packet.dst, udpp.dstport)
					path_key = (this_dpid, packet.src, packet.dst, 200)
				elif tcpp:
					if tcpp.dstport == 80 or tcpp.srcport == 80: # HTTP Service
						log.debug("HTTP directed traffic detected: %s -> %s", packet.src, packet.dst)
						path_key = (this_dpid, packet.src, packet.dst, 80)
					elif tcpp.dstport == 200 or tcpp.srcport == 200:
						log.debug("TCP traffic detected: %s (src port %s) -> %s (dst port %s)", packet.src, tcpp.srcport, packet.dst, tcpp.dstport)
						path_key = (this_dpid, packet.src, packet.dst, 200)
				else:
					log.debug("Unknown traffic detected: %s -> %s", packet.src, packet.dst)
					flood()
					return

				try:
					next_hop_dpid = self.portmap[path_key]
					outport = self.adjacency[this_dpid][next_hop_dpid]
					log.debug("Forwarding to next hop: %s via port %d", next_hop_dpid, outport)
					install_fwdrule(event, packet, outport)

				except KeyError:
					log.debug("No switch path found for %s -> %s", packet.src, packet.dst)
					try:
						outport = self.switch_to_hosts_ports[(this_dpid, packet.dst)]
						log.debug("Forwarding to host %s via port %d", packet.dst, outport)
						install_fwdrule(event, packet, outport)
					except KeyError:
						log.debug("No mapping found for host %s, flooding", packet.dst)
						return
						# flood()

			except AttributeError:
				log.debug("packet type has no transport ports, flooding")
				# flood and install the flow table entry for the flood
				install_fwdrule(event,packet,of.OFPP_FLOOD)

			log.debug("--------------------End Forwarding--------------------")

		forward()

def launch():
	# Ejecute spanning tree para evitar problemas con topologías con bucles
	pox.openflow.discovery.launch()
	pox.openflow.spanning_tree.launch()

	core.registerNew(CustomSlice)

