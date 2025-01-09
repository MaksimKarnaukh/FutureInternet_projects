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

log = core.getLogger()

class StatsCollector(EventMixin):

    def __init__(self, timer_interval=5):
        self.listenTo(core.openflow)
        self.stats = {} # store statistics per switch
        self.paths = {} # store paths per flow
        # remove txt files that start with flow_stats
        for file in os.listdir():
            if file.startswith('flow_stats'):
                os.remove(file)
            if file.startswith('port_stats'):
                os.remove(file)

        self.interval = timer_interval # timer interval in seconds
        Timer(self.interval, self._timer_func, recurring=True) # library timer function
        log.info("StatsCollector initialized with timer interval %s seconds", self.interval)

    def _handle_ConnectionUp(self, event):
        """
        Handles new switch connection event
        """
        log.debug("Switch %s has connected.", dpidToStr(event.dpid))
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

        connection.send(of.ofp_stats_request(
            body=of.ofp_aggregate_stats_request(
                match=of.ofp_match(), # match criteria (empty = match all flows)
                table_id=0xff, # table ID (0xff = all tables)
                out_port=of.OFPP_NONE # output port (OFPP_NONE = no specific port)
            )
        )) # request aggregate stats
        connection.send(of.ofp_stats_request(body=of.ofp_table_stats_request())) # request table stats
        connection.send(of.ofp_stats_request(body=of.ofp_queue_stats_request())) # request queue stats

    def _handle_FlowStatsReceived(self, event):
        """
        Handles flow stats received event
        """
        # Update received flow stats
        switch_identifier = dpid_to_str(event.connection.dpid)
        log.info("FlowStats received from %s", switch_identifier)

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
        filename = "flow_stats_" + dpid_to_str(event.connection.dpid) + ".txt"
        self.write_stats_to_output(self.stats[event.connection.dpid], filename, switch_identifier)

        # Update paths and traffic
        self.update_paths(stats_data, switch_identifier)
        # Log the paths and their traffic statistics
        self.log_paths()

    def _handle_PortStatsReceived(self, event):
        """
        Handles port stats received event
        """
        switch_identifier = dpid_to_str(event.connection.dpid)
        log.info("PortStats received from %s", switch_identifier)

        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid not in self.stats:
            self.stats[event.connection.dpid] = {}
        self.stats[event.connection.dpid]['port_stats'] = stats_data

        filename = "port_stats_" + switch_identifier + ".txt"
        self.write_stats_to_output(stats_data, filename, switch_identifier, stats_type='Port')

    def _handle_AggregateStatsReceived(self, event):
        """
        Handles aggregate stats received event
        """
        switch_identifier = dpid_to_str(event.connection.dpid)
        log.info("AggregateStats received from %s", switch_identifier)
        stats_data = flow_stats_to_list(event.stats)
        if event.connection.dpid not in self.stats:
            self.stats[event.connection.dpid] = {}
        self.stats[event.connection.dpid]['aggregate_stats'] = stats_data
        filename = "aggregate_stats_" + switch_identifier + ".txt"
        log.debug("Aggregate stats: \n%s", stats_data)

    def _handle_TableStatsReceived(self, event):
        """
        Handles table stats received event
        """
        pass

    def _handle_QueueStatsReceived(self, event):
        """
        Handles queue stats received event
        """
        pass

    ### Helper functions ###

    def calculate_averages(self, stats):
        for flow in stats:
            # calculate average packet rate and average byte rate
            duration = flow["duration_sec"] + flow["duration_nsec"] / 1e9
            average_packet_rate = flow["packet_count"] / duration
            average_byte_rate = flow["byte_count"] / duration
            flow['average_packet_rate'] = average_packet_rate
            flow['average_byte_rate'] = average_byte_rate

    def write_stats_to_output(self, data, filename, switch_identifier, stats_type='Flow'):
        """
        Append flow statistics data to a txt file
        """
        try:
            if not filename:
                str_stream = self.build_flow_stats_string(data, switch_identifier)
                log.info(str_stream)
                return
            with open(filename, 'a') as f:
                str_stream = ""
                if stats_type == 'Flow':
                    str_stream = self.build_flow_stats_string(data, switch_identifier)
                elif stats_type == 'Port':
                    str_stream = self.build_port_stats_string(data, switch_identifier)
                else:
                    log.error("Invalid stats type")
                f.write(str_stream)
                log.debug(stats_type + "-Level " + "Statistics at Switch " + switch_identifier + " written to " + filename)
        except Exception as e:
            log.error("Error writing flow stats to %s: %s", filename, e)

    def build_flow_stats_string(self, data, switch_identifier):
        """
        Convert flow statistics data to a string format
        """
        try:
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

        except Exception as e:
            log.error("Error building flow stats string: %s", e)

    def build_port_stats_string(self, port_stats, switch_identifier):
        """
        Convert port stats to a pretty string
        """

        try:
            timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            str_stream = ""

            headers = list(port_stats[0].keys())

            column_widths = {header: max(len(header), max(len(str(port[header])) for port in port_stats)) for header in
                             headers}

            header_row = " | ".join("{:<{width}}".format(header, width=column_widths[header]) for header in headers)

            eq_len = len(header_row)
            str_stream = eq_len * '=' + "\n"
            Port_Level_str = "Port-Level Statistics for Switch " + switch_identifier + " at " + str(timestamp_now)
            Port_Level_str_len = len(Port_Level_str)
            eq_len_port_level = eq_len - Port_Level_str_len
            str_stream += ('=' * (eq_len_port_level // 2)) + Port_Level_str + (
                        '=' * (eq_len_port_level // 2 + eq_len_port_level % 2)) + "\n"
            str_stream += eq_len * '=' + "\n"

            str_stream += header_row + "\n"
            str_stream += "-" * len(header_row) + "\n"

            for port in port_stats:
                row = " | ".join(
                    "{:<{width}}".format(str(port[header]), width=column_widths[header]) for header in headers)
                str_stream += row + "\n"

            str_stream += "-" * len(header_row) + "\n"

            total_port_stats = self.get_port_stats_total(port_stats)
            row = " | ".join(
                "{:<{width}}".format(str(total_port_stats[header]), width=column_widths[header]) for header in headers)
            str_stream += row + "\n"

            str_stream += "=" * len(header_row) + "\n\n"
            return str_stream

        except Exception as e:
            log.error("Error building port stats string: %s", e)

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
        total['port_no'] = "Total"
        return total

    # def reconstruct_paths(self, flow_stats, switch, paths):
    #     """
    #     Reconstruct paths incrementally using flow statistics from a single switch.
    #     Args:
    #         flow_stats: List of flow stats from the current switch.
    #         switch: Identifier of the current switch (e.g., "s1").
    #         paths: Global dictionary of paths being constructed.
    #                Format: { (src_ip, dst_ip): [list_of_switches] }
    #     Returns:
    #         Updated paths with new data from the current switch.
    #     """
    #     for flow in flow_stats:
    #         # Extract source and destination IPs
    #         src_ip = flow['nw_src']
    #         dst_ip = flow['nw_dst']
    #
    #         # If the path does not exist, initialize it with the current switch
    #         if (src_ip, dst_ip) not in paths:
    #             paths[(src_ip, dst_ip)] = [switch]
    #         # Append the current switch if not already in the path
    #         elif switch not in paths[(src_ip, dst_ip)]:
    #             paths[(src_ip, dst_ip)].append(switch)
    #
    #     return paths
    #
    # def aggregate_traffic(self, flow_stats, paths):
    #     """
    #     Aggregate traffic for each path.
    #     Args:
    #         flow_stats: A dictionary of flow stats from each switch.
    #         paths: A dictionary of paths { (src_ip, dst_ip): [list_of_switches] }.
    #     Returns:
    #         A dictionary of path traffic { (src_ip, dst_ip): total_bytes }.
    #     """
    #     path_traffic = {}
    #
    #     for (src_ip, dst_ip), path in paths.items():
    #         total_bytes = 0
    #         for switch in path:
    #             if switch in flow_stats:
    #                 for flow in flow_stats[switch]:
    #                     if flow['nw_src'] == src_ip and flow['nw_dst'] == dst_ip:
    #                         total_bytes += flow['byte_count']
    #         path_traffic[(src_ip, dst_ip)] = total_bytes
    #
    #     return path_traffic
    #
    # def get_top_talkers(self, path_traffic, top_n=5):
    #     """
    #     Get the top N talkers based on path traffic.
    #     Args:
    #         path_traffic: A dictionary of path traffic { (src_ip, dst_ip): total_bytes }.
    #         top_n: Number of top talkers to return.
    #     Returns:
    #         A sorted list of top N talkers [(path, total_bytes)].
    #     """
    #     sorted_paths = sorted(path_traffic.items(), key=lambda x: x[1], reverse=True)
    #     return sorted_paths[:top_n]

    def update_paths(self, flow_stats, switch):
        """
        Updates paths based on flow stats from the current switch and tracks traffic.
        """
        for flow in flow_stats:
            # Extract source and destination IPs
            src_ip = flow['match']['nw_src']
            dst_ip = flow['match']['nw_dst']
            protocol = flow['match']['dl_type']

            # Create a unique path identifier
            path_key = (src_ip, dst_ip, protocol)

            # If the path doesn't exist, initialize it
            if path_key not in self.paths:
                self.paths[path_key] = {
                    'path': [switch],
                    'total_bytes': [0, 0], # [total_bytes_overall, total_bytes_in_current_active_flow]
                    'total_packets': [0, 0], # [total_packets_overall, total_packets_in_current_active_flow]
                    'counting_switch': None
                }

            if self.paths[path_key]['counting_switch'] is None:
                self.paths[path_key]['counting_switch'] = switch
            if self.paths[path_key]['counting_switch'] == switch:
                # Update traffic statistics
                if flow['byte_count'] < self.paths[path_key]['total_bytes'][1]:
                    # update total_bytes_overall and total_packets_overall
                    self.paths[path_key]['total_bytes'][0] += self.paths[path_key]['total_bytes'][1]
                    self.paths[path_key]['total_packets'][0] += self.paths[path_key]['total_packets'][1]

                    # A new flow has started
                    self.paths[path_key]['total_bytes'][1] = flow['byte_count']
                    self.paths[path_key]['total_packets'][1] = flow['packet_count']
                else:
                    self.paths[path_key]['total_bytes'][1] = flow['byte_count']
                    self.paths[path_key]['total_packets'][1] = flow['packet_count']

                # print the total_bytes as a list
                log.debug("total_bytes: %s, for path key %s", self.paths[path_key]['total_bytes'], path_key)

            # Add the current switch to the path if not already included
            if switch not in self.paths[path_key]['path']:
                self.paths[path_key]['path'].append(switch)

    def log_paths(self):
        """
        Logs all paths and their traffic statistics.
        """
        log.info("Current Paths and Traffic Statistics:")
        for (src_ip, dst_ip, protocol), data in self.paths.items():
            log.info(
                "Path from %s to %s (protocol %s) via switches %s: Total Bytes = %d, Total Packets = %d",
                src_ip, dst_ip, protocol, " -> ".join(data['path']), data['total_bytes'][0]+data['total_bytes'][1], data['total_packets'][0]+data['total_packets'][1]
            )


def launch():

    core.registerNew(StatsCollector)

