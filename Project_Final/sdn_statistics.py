"""
SDN Statistics → In order to perform network monitoring, flow statistics can be obtained from
the switch (e.g. flow duration, number of packets, etc.). Some statistics can be obtained from
openflow or different tools (e.g. sflow). The idea here would be to implement a SDN
environment (using any controller) where you show what statistics you can get with any tool
(openflow, sflow or more).
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *

from pox.lib.util import dpid_to_str
from pox.lib.util import dpidToStr
from pox.lib.recoco import Timer
from pox.openflow.of_json import *

import csv
import os
from datetime import datetime

# import matplotlib.pyplot as plt

log = core.getLogger()

class StatsCollector(EventMixin):

    def __init__(self, timer_interval=5):
        self.listenTo(core.openflow)
        self.stats = {}  # Store stats per switch

        self.interval = timer_interval  # Timer interval in seconds
        Timer(self.interval, self._timer_func, recurring=True)
        log.info("StatsCollector initialized with timer interval %s seconds", self.interval)

    def _handle_ConnectionUp(self, event):
        dpid = dpidToStr(event.dpid)
        log.debug("Switch %s has connected.", dpid)
        self.request_stats(event.connection)

    def _timer_func(self):
        log.debug("Number of switches: %i", len(core.openflow._connections))
        log.debug(core.openflow._connections.values())

        for connection in core.openflow._connections.values():
            self.request_stats(connection)
        log.debug("Sent %i flow/port stats request(s)", len(core.openflow._connections))

    def request_stats(self, connection):
        dpid = dpidToStr(connection.dpid)
        log.debug("Requesting stats from switch %s", dpid)
        connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request()))
        connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))

    # def _handle_StatsReply(self, event):
    #     log.info(f"StatsReply from switch {dpid_to_str(event.connection.dpid)}")
    #     stats_data = []
    #     for flow in event.stats:
    #         stats_data.append({
    #             'Match': str(flow.match),
    #             'Packet Count': flow.packet_count,
    #             'Byte Count': flow.byte_count,
    #             'Duration': flow.duration_sec
    #         })
    #     self.stats[event.connection.dpid] = stats_data
    #     self.save_to_csv(stats_data, f"stats_{dpid_to_str(event.connection.dpid)}.csv")
    #     self.display_stats(stats_data)

    def _handle_FlowStatsReceived(self, event):
        log.info("FlowStats received from %s", dpid_to_str(event.connection.dpid))
        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid not in self.stats:
            self.stats[event.connection.dpid] = {}
        self.stats[event.connection.dpid]['flow_stats'] = stats_data
        filename = "flow_stats_" + dpid_to_str(event.connection.dpid) + ".csv"
        self.save_to_csv(stats_data, filename)
        self.display_stats(stats_data)

    def _handle_PortStatsReceived(self, event):
        log.info("PortStats received from %s", dpid_to_str(event.connection.dpid))
        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid not in self.stats:
            self.stats[event.connection.dpid] = {}
        self.stats[event.connection.dpid]['port_stats'] = stats_data
        filename = "port_stats_" + dpid_to_str(event.connection.dpid) + ".csv"
        self.save_to_csv(stats_data, filename)
        self.display_stats(stats_data)

    # def save_to_csv(self, data, filename):
    #     with open(filename, 'w', newline='') as csvfile:
    #         fieldnames = ['Match', 'Packet Count', 'Byte Count', 'Duration']
    #         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    #         writer.writeheader()
    #         writer.writerows(data)
    #     log.info(f"Stats saved to {filename}")
    def save_to_csv(self, data, filename):
        if not data:
            log.warning("No data to save for %s", filename)
            return

        log.debug("Data to save: %s", data)

        # with open(filename, 'w', newline='') as csvfile:
        #     fieldnames = data[0].keys() if data else []
        #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #     writer.writeheader()
        #     writer.writerows(data)
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['Timestamp', 'Match', 'Packet Count', 'Byte Count', 'Duration']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for row in data:
                row['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow(row)

        log.info("Stats saved to %s", filename)

    # def display_stats(self, stats):
    #     table = []
    #     for flow in stats:
    #         table.append([
    #             flow['Match'], flow['Packet Count'], flow['Byte Count'], flow['Duration']
    #         ])
    #     log.info("\n" + tabulate(table, headers=["Match", "Packets", "Bytes", "Duration"]))
    def display_stats(self, stats):
        if not stats:  # Handle empty stats gracefully
            log.warning("No stats to display")
            return
        table = [[str(stat[key]) for key in stat] for stat in stats]
        headers = list(stats[0].keys()) if stats else []
        # log.info("\n" + tabulate(table, headers=headers))
        log.info("\n" + table)

    def plot_traffic(self, stats):
        flows = [flow['Match'] for flow in stats]
        packet_counts = [flow['Packet Count'] for flow in stats]
        # plt.bar(flows, packet_counts)
        # plt.xlabel("Flows")
        # plt.ylabel("Packet Count")
        # plt.title("Traffic per Flow")
        # plt.show()

def launch():
    core.registerNew(StatsCollector)

