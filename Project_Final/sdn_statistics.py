"""
SDN Statistics → In order to perform network monitoring, flow statistics can be obtained from
the switch (e.g. flow duration, number of packets, etc.). Some statistics can be obtained from
openflow or different tools (e.g. sflow). The idea here would be to implement a SDN
environment (using any controller) where you show what statistics you can get with any tool
(openflow, sflow or more).
"""
"""Collected statistics

"""


from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *

from pox.lib.util import dpid_to_str
from pox.lib.util import dpidToStr
from pox.lib.recoco import Timer
from pox.openflow.of_json import *
import os
from datetime import datetime
import csv
# import matplotlib.pyplot as plt

log = core.getLogger()

class StatsCollector(EventMixin):

    def __init__(self, timer_interval=5):
        self.listenTo(core.openflow)
        self.stats = {} # store statistics per switch
        # remove txt files that start with flow_stats
        for file in os.listdir():
            if file.startswith('flow_stats') and file.endswith('.txt'):
                os.remove(file)


        self.interval = timer_interval # timer interval in seconds
        Timer(self.interval, self._timer_func, recurring=True) # library timer function
        log.info("StatsCollector initialized with timer interval %s seconds", self.interval)

    def _handle_ConnectionUp(self, event):
        """
        Handles new switch connection event
        """
        dpid = dpidToStr(event.dpid)
        log.debug("Switch %s has connected.", dpid)
        self.request_stats(event.connection)

    def _timer_func(self):
        """
        Sends flow/port stats request to all connected switches
        """
        for connection in core.openflow._connections.values():
            self.request_stats(connection)
        log.debug("Sent %i flow/port stats request(s)", len(core.openflow._connections))

    def request_stats(self, connection):
        """
        Sends flow/port stats request to the switch (= connection)
        """
        dpid = dpidToStr(connection.dpid) # datapath id of the switch
        log.debug("Requesting stats from switch %s", dpid)
        connection.send(of.ofp_stats_request(body=of.ofp_flow_stats_request())) # request flow stats
        connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request())) # request port stats


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

    def append_to_txt(self, data, filename, diff: dict, switch_identifier):
        with open(filename, 'a') as f:
            nr_of_active_flows = len(data)
            # f.write(f"Flow-Level Statistics at Switch" + switch_identifier + "\n")
            # f.write(f"Nr of active flows: {nr_of_active_flows}\n")
            #
            # for flow in data:
            #     matching = flow["match"]
            #     tp_src = matching['tp_src'] if 'tp_src' in matching else None
            #     tp_dst = matching['tp_dst'] if 'tp_dst' in matching else None
            #     duration = flow['duration_sec'] + flow['duration_nsec'] / 1e9 # Convert to seconds
            #
            #     f.write(f"Flow-Level Statistics at Switch" + switch_identifier + "\n")
            #     f.write(f"Nr of active flows: {len(data)}\n")
            #     f.write(f"Flow matching source: {matching['nw_src']},{matching['dl_src']}")
            #     if tp_src:
            #         f.write(f"source port: {tp_src}")
            #     f.write(f"and destination: {matching['nw_dst']},{matching['dl_dst']}")
            #     if tp_dst:
            #         f.write(f"destination port: {tp_dst}")
            #     f.write(f"Statistics since start:\n")
            #     f.write(f"\tNumber of packets: {flow['packet_count']}, averaging {flow['packet_count']/duration} per second\n")
            #     f.write(f"\tNumber of bytes: {flow['byte_count']}, averaging {flow['byte_count']/duration} per second\n")
            #     f.write(f"\tDuration: {duration} seconds\n")
            #     if "diff" in flow:
            #         f.write(f"Statistics since last request:\n")
            #         for diff in flow["diff"]:
            #             f.write(f"\tNumber of packets: {diff['packet_count']}, averaging {diff['packet_count']/duration} per second\n")
            #             f.write(f"\tNumber of bytes: {diff['byte_count']}, averaging {diff['byte_count']/duration} per second\n")
            #             f.write(f"\tDuration: {diff['duration']} seconds\n")
            #     f.write("\n")
            # print(f"Flow-Level Statistics at Switch {switch_identifier} written to {filename}")

            timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            f.write("Flow-Level Statistics for Switch " + switch_identifier + " at " + str(timestamp_now) + "\n")
            f.write("Nr of active flows: " + str(nr_of_active_flows) + "\n\n")
            for flow in data:
                matching = flow["match"]
                tp_src = matching['tp_src'] if 'tp_src' in matching else None
                tp_dst = matching['tp_dst'] if 'tp_dst' in matching else None
                duration = round(flow['duration_sec'] + flow['duration_nsec'] / 1e9, 3)
                ip_protocol = matching['dl_type'] if 'dl_type' in matching else None

                f.write("Flow matching (protocol: " + ip_protocol + ") source: " + str(matching['nw_src']) + ", " + str(matching['dl_src']))
                if tp_src:
                    f.write(", port: " + str(tp_src))
                f.write(" and destination: " + str(matching['nw_dst']) + ", " + str(matching['dl_dst']))
                if tp_dst:
                    f.write(", port: " + str(tp_dst))
                f.write("\nStatistics since start:\n")
                f.write("\tNumber of packets: " + str(flow['packet_count']) + ", averaging " + str(round(flow['packet_count']/duration, 3)) + " per second\n")
                f.write("\tNumber of bytes: " + str(flow['byte_count']) + ", averaging " + str(round(flow['byte_count']/duration, 3)) + " per second\n")
                f.write("\tDuration: " + str(duration) + " seconds\n")
                if "diff" in flow:
                    f.write("Statistics since last request:\n")
                    diff = flow["diff"]
                    diff_duration = round(diff['duration_sec'] + diff['duration_nsec'] / 1e9, 3)
                    f.write("\tNumber of packets: " + str(diff['packet_count']) + ", averaging " + str(round(diff['packet_count']/duration, 3)) + " per second\n")
                    f.write("\tNumber of bytes: " + str(diff['byte_count']) + ", averaging " + str(round(diff['byte_count']/duration, 3)) + " per second\n")
                    f.write("\tDuration: " + str(diff_duration) + " seconds\n")
                f.write("\n")
            log.debug("Flow-Level Statistics at Switch " + switch_identifier + " written to " + filename)
            f.write("="*100 + "\n")

    def calculate_diff(self, old_stats, new_stats):
        """
        Calculate the difference between two sets of flow statistics (old and new) and return the difference. Only if the flow is present in the new stats and old stats
        """
        for new_flow in new_stats:
            diff = {}
            for old_flow in old_stats:
                if new_flow['match'] == old_flow['match']:
                    diff = {
                        'match': new_flow['match'],
                        'packet_count': new_flow['packet_count'] - old_flow['packet_count'],
                        'byte_count': new_flow['byte_count'] - old_flow['byte_count'],
                        'duration_sec': new_flow['duration_sec'] - old_flow['duration_sec'],
                        'duration_nsec': new_flow['duration_nsec'] - old_flow['duration_nsec']
                    }
                    break
            
            # Append diff to new_flow if diff is not empty
            if diff:
                new_flow['diff'] = diff 

    def _handle_FlowStatsReceived(self, event):
        """
        Handles flow stats received event
        """
        switch_identifier = dpid_to_str(event.connection.dpid)
        log.info("FlowStats received from %s", dpid_to_str(event.connection.dpid))

        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid in self.stats and 'flow_stats' in self.stats[event.connection.dpid]:
            diff = self.calculate_diff(new_stats=stats_data, old_stats=self.stats[event.connection.dpid]['flow_stats'])
        if event.connection.dpid not in self.stats: # event.connection.dpid is the datapath id of the switch
            self.stats[event.connection.dpid] = {}
        self.stats[event.connection.dpid]['flow_stats'] = stats_data
        filename = "flow_stats_" + dpid_to_str(event.connection.dpid)
        self.append_to_txt(stats_data, filename+".txt", diff, switch_identifier)
        self.save_to_csv(stats_data, filename+".csv")
        self.display_flow_stats_in_terminal(stats_data)

    def _handle_PortStatsReceived(self, event):
        """
        Handles port stats received event
        """
        log.info("PortStats received from %s", dpid_to_str(event.connection.dpid))
        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid not in self.stats: # event.connection.dpid is the datapath id of the switch
            self.stats[event.connection.dpid] = {}
        self.stats[event.connection.dpid]['port_stats'] = stats_data
        filename = "port_stats_" + dpid_to_str(event.connection.dpid) + ".csv"
        self.save_to_csv(stats_data, filename)
        self.display_port_stats_in_terminal(stats_data)
        # TODO: create a way to append to a txt file, together with printing to terminal (which is already done)

    def save_to_csv(self, data, filename):
        """
        Save statistics data to a csv file
        """
        if not data:
            log.warning("No data to save for %s", filename)
            return

        # log.debug("Data to save: %s", data)

        "below is for debugging purposes"
        str_stream = "\n[\n"
        for d in data:
            str_stream += "\t{\n"
            for key in d:
                str_stream += "\t\t" + key + ": " + str(d[key]) + "\n"
            str_stream += "\t},\n"
        str_stream += "\n]\n"
        log.debug("Data to save:\n %s", str_stream)
        "above is for debugging purposes"

        #TODO: the saving to csv is not necessarily optimal, especially for flow stats.
        # Plus, notice that it overwrites the file everytime, which might be what we want idk.

        with open(filename, 'w', newline='') as csvfile:
            fieldnames = data[0].keys() if data else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        # file_exists = os.path.isfile(filename)
        # with open(filename, 'a', newline='') as csvfile:
        #     fieldnames = ['Timestamp', 'Match', 'Packet Count', 'Byte Count', 'Duration']
        #     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #
        #     if not file_exists:
        #         writer.writeheader()
        #
        #     for row in data:
        #         row['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        #         writer.writerow(row)

        log.info("Stats saved to %s", filename)

    def flow_stats_to_pretty_string(self, stats):

        # TODO: convert flow stats to a pretty string
        pass

    def display_flow_stats_in_terminal(self, stats):
        if not stats:
            log.warning("No flow statistics to display")
            return

        # TODO: display in some pretty table format, similar to the display_port_stats_in_terminal method
        #  whatever code is below this might be bs (also, tabulate library doesnt work)

        table = [[str(stat[key]) for key in stat] for stat in stats]
        headers = list(stats[0].keys()) if stats else []
        # log.info("\n" + tabulate(table, headers=headers))
        # log.info("\n" + table)

    def port_stats_to_pretty_string(self, port_stats):
        """
        Convert port stats to a pretty string
        """

        try:
            str_stream = ""

            headers = list(port_stats[0].keys())

            column_widths = {header: max(len(header), max(len(str(port[header])) for port in port_stats)) for header in
                             headers}

            header_row = " | ".join("{:<{width}}".format(header, width=column_widths[header]) for header in headers)
            str_stream += "=" * len(header_row) + "\n"
            str_stream += header_row + "\n"
            str_stream += "-" * len(header_row) + "\n"

            for port in port_stats:
                row = " | ".join(
                    "{:<{width}}".format(str(port[header]), width=column_widths[header]) for header in headers)
                str_stream += row + "\n"

            str_stream += "=" * len(header_row) + "\n"
            return str_stream

        except Exception as e:
            log.error("Error in port_stats_to_pretty_string: %s", e)


    def display_port_stats_in_terminal(self, port_stats):
        """
        Display port statistics in a pretty table format in the terminal
        """

        if not port_stats:
            log.info("No port statistics available.")
            return
        str_stream = self.port_stats_to_pretty_string(port_stats)
        log.info("\n" + str_stream)

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

