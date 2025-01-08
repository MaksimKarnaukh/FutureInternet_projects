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
        # active_talkers: dict switch -> bytes
        self.active_talkers = {'Network': []}

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

        connection.send(of.ofp_stats_request(body=of.ofp_aggregate_stats_request())) # request aggregate stats
        connection.send(of.ofp_stats_request(body=of.ofp_table_stats_request())) # request table stats
        connection.send(of.ofp_stats_request(body=of.ofp_queue_stats_request())) # request queue stats
        # connection.send(of.ofp_stats_request(body=of.ofp_group_stats_request())) # request group stats
        # connection.send(of.ofp_stats_request(body=of.ofp_group_desc_stats_request())) # request group desc stats
        # connection.send(of.ofp_stats_request(body=of.ofp_group_features_stats_request())) # request group features stats
        # connection.send(of.ofp_stats_request(body=of.ofp_meter_stats_request())) # request meter stats
        # connection.send(of.ofp_stats_request(body=of.ofp_meter_config_stats_request())) # request meter config stats
        # connection.send(of.ofp_stats_request(body=of.ofp_meter_features_stats_request())) # request meter features stats

    def calculate_averages(self, stats):
        for flow in stats:
            # calculate average packet rate and average byte rate
            duration = flow["duration_sec"] + flow["duration_nsec"] / 1e9
            average_packet_rate = flow["packet_count"] / duration
            average_byte_rate = flow["byte_count"] / duration
            flow['average_packet_rate'] = average_packet_rate
            flow['average_byte_rate'] = average_byte_rate
    def _handle_FlowStatsReceived(self, event):
        """
        Handles flow stats received event
        """
        # Update received flow stats
        switch_identifier = dpid_to_str(event.connection.dpid)
        log.info("FlowStats received from %s", dpid_to_str(event.connection.dpid))

        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid in self.stats and 'flow_stats' in self.stats[event.connection.dpid]:
            # calculate difference between old and new flow stats
            old_nr_flows = len(self.stats[event.connection.dpid]['flow_stats'])
            nr_added_flows, nr_removed_flows = self.calculate_diff(new_stats=stats_data, old_stats=self.stats[event.connection.dpid]['flow_stats'])
            self.stats[event.connection.dpid]['other_stats'] = { 'nr_added_flows': nr_added_flows, 'nr_removed_flows': nr_removed_flows, 'old_nr_flows': old_nr_flows}


        if event.connection.dpid not in self.stats: # event.connection.dpid is the datapath id of the switch
            self.stats[event.connection.dpid] = {}
        self.calculate_averages(stats_data)
        self.stats[event.connection.dpid]['flow_stats'] = stats_data
        
        # Use the updated stats
        filename = "flow_stats_" + dpid_to_str(event.connection.dpid)

        self.append_to_txt(self.stats[event.connection.dpid], filename+".txt", switch_identifier)
        self.save_to_csv(stats_data, filename+".csv")
        self.display_flow_stats_in_terminal(stats_data)

    def append_to_txt(self, data, filename, switch_identifier):
        """
        Append flow statistics data to a txt file
        """
        with open(filename, 'a') as f:
            str_stream = self.flow_stats_string(data, switch_identifier)
            f.write(str_stream)
            log.debug("Flow-Level Statistics at Switch " + switch_identifier + " written to " + filename)

    def flow_stats_string(self, data, switch_identifier):
        """
        Convert flow statistics data to a string format
        """
        eq_len = 150
        str_stream = eq_len*'=' + "\n"
        timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        Flow_Level_str = "Flow-Level Statistics for Switch " + switch_identifier + " at " + str(timestamp_now)
        Flow_Level_str_len = len(Flow_Level_str)
        eq_len_flow_level = eq_len - Flow_Level_str_len
        str_stream += ('=' * (eq_len_flow_level//2 )) + Flow_Level_str + ('=' * (eq_len_flow_level//2+ eq_len_flow_level%2)) + "\n"
        str_stream += eq_len*'=' + "\n"
        if not data:
            log.warning("No flow statistics to display")
            return str_stream
        flow_stats = data['flow_stats']
        
        nr_of_active_flows = len(flow_stats)
        #  get current timestamp
        # append to string stream
        # append number of active flows
        added_removed_flow_strings = ""
        if 'other_stats' in data:
            other_stats = data['other_stats']
            added_removed_flow_strings = " with " + str(other_stats["nr_added_flows"]) + " new flows and " + str(other_stats["nr_removed_flows"])+' out of the previous '+ str(other_stats["old_nr_flows"]) + " removed "
        str_stream += str(nr_of_active_flows) + " active flows" + added_removed_flow_strings +  "\n\n"
        # sort flows by byte rate, highest first
        flow_stats.sort(key=lambda x: x["diff"]['average_byte_rate'] if "diff" in x else x['average_byte_rate'], reverse=True)
        if flow_stats:
            str_stream += "Statistics for each flow (sorted by byte rate):\n"
        # iterate over each flow
        indentation = "\t"
        for flow in flow_stats:
            # get matching fields
            matching = flow["match"]
            tp_src = matching['tp_src'] if 'tp_src' in matching else None
            tp_dst = matching['tp_dst'] if 'tp_dst' in matching else None
            # calculate duration
            duration = round(flow['duration_sec'] + flow['duration_nsec'] / 1e9, 3)
            # get ip protocol
            ip_protocol = matching['dl_type'] if 'dl_type' in matching else None
            # append to string stream
            str_stream +=indentation+"Flow matching (protocol: " + ip_protocol + ") source: " + str(matching['nw_src']) + ", " + str(matching['dl_src'])
            if tp_src:
                str_stream += ", port: " + str(tp_src)
            str_stream += " and destination: " + str(matching['nw_dst']) + ", " + str(matching['dl_dst'])
            if tp_dst:
                str_stream += ", port: " + str(tp_dst)
            str_stream += "\n"
            # statistics since start of flow
            indentation += "\t"
            str_stream += indentation + "Statistics since start:\n"
            indentation += "\t"
            str_stream +=indentation+"Number of packets: " + str(flow['packet_count']) + ", averaging " + str(round(flow['packet_count']/duration, 3)) + " per second\n"
            str_stream +=indentation+"Number of bytes: " + str(flow['byte_count']) + ", averaging " + str(round(flow['byte_count']/duration, 3)) + " per second\n"
            str_stream +=indentation+"Duration: " + str(duration) + " seconds\n"
            indentation = indentation[:-1]
            # statistics since last request
            if "diff" in flow:
                # remove one level of indentation
                str_stream +=indentation+"Statistics since last request:\n"
                diff = flow["diff"]
                diff_duration = round(diff['duration_sec'] + diff['duration_nsec'] / 1e9, 3)
                indentation += "\t"
                str_stream +=indentation+"Number of packets: " + str(diff['packet_count']) + ", averaging " + str(round(diff['average_packet_rate'], 3)) + " per second\n"
                str_stream +=indentation+"Number of bytes: " + str(diff['byte_count']) + ", averaging " + str(round(diff['average_byte_rate'], 3)) + " per second\n"
                str_stream +=indentation+"Duration: " + str(diff_duration) + " seconds\n"
                indentation = indentation[:-1]
            indentation = indentation[:-1]
            str_stream +="\n"
        return str_stream

    def calculate_diff(self, old_stats, new_stats):
        """
        Calculate the difference between two sets of flow statistics (old and new) and return the difference. Only if the flow is present in the new stats and old stats
        """
        nr_new_flows = len(new_stats)
        nr_old_flows = len(old_stats)
        flows_matched = 0

        for new_flow in new_stats:
            diff = {}
            for old_flow in old_stats:
                if new_flow['match'] == old_flow['match']:
                    flows_matched += 1
                    diff = {
                        'match': new_flow['match'],
                        'packet_count': new_flow['packet_count'] - old_flow['packet_count'],
                        'byte_count': new_flow['byte_count'] - old_flow['byte_count'],
                        'duration_sec': new_flow['duration_sec'] - old_flow['duration_sec'],
                        'duration_nsec': new_flow['duration_nsec'] - old_flow['duration_nsec']
                    }
                    total_duration = diff['duration_sec'] + diff['duration_nsec'] / 1e9
                    average_packet_rate = diff['packet_count'] / total_duration
                    average_byte_rate = diff['byte_count'] / total_duration
                    diff['average_packet_rate'] = average_packet_rate
                    diff['average_byte_rate'] = average_byte_rate
                    break
                

            # Append diff to new_flow if diff is not empty
            if diff:
                new_flow['diff'] = diff 
        nr_added_flows = nr_new_flows - flows_matched
        nr_removed_flows = nr_old_flows - flows_matched 
        return  nr_added_flows, nr_removed_flows
        





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

    def get_port_stats_total(self, port_stats):
        """
        Get total port statistics
        """
        total = {}
        for port in port_stats:
            for key in port:
                if key == "port_no":
                    continue
                if key not in total:
                    total[key] = port[key]
                else:
                    total[key] += port[key]
        return total

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

