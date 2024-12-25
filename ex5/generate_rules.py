import re


def parse_tree(tree_file):
    """
    Parses the decision tree file and extracts conditions and actions.
    """
    with open(tree_file, 'r') as f:
        lines = f.readlines()

    ip_proto = []
    src_port = []
    dst_port = []
    conditions = []

    for line in lines:
        line = line.strip()

        if not line or line.startswith("#"):
            continue
        try:
            if "when" in line:
                when_match = re.match(r"when\s*(.*?)\s*then\s*(\d+);?", line)
                if when_match:
                    condition = when_match.group(1).strip()
                    class_ = int(when_match.group(2).strip())
                    conditions.append((condition, class_))
            else:
                match = re.search(r"=\s*(\[[^\]]*\])", line)
                if "ip_proto" in line and match:
                    ip_proto = eval(match.group(1))
                elif "src_port" in line and match:
                    src_port = eval(match.group(1))
                elif "dst_port" in line and match:
                    dst_port = eval(match.group(1))
        except Exception as e:
            print(f"Error parsing line: {line}\n{e}")

    return ip_proto, src_port, dst_port, conditions



# def generate_rules(ip_proto, src_port, dst_port, conditions):
#     """
#     Generates match-action table rules based on the decision tree.
#     """
#     feature1_rules = []
#     feature2_rules = []
#     feature3_rules = []
#     forwarding_rules = []
#
#     # Action selectors
#     action_select1 = 1
#     action_select2 = 1
#     action_select3 = 1
#
#     # Unique ranges for matching
#     proto_ranges = {}
#     src_port_ranges = {}
#     dst_port_ranges = {}
#
#     for condition, action in conditions:
#         # Extract ip_proto, src_port, dst_port conditions
#         proto_match = re.search(r"ip_proto[<=>]+([\d.]+)", condition)
#         src_match = re.search(r"src_port[<=>]+([\d.]+)", condition)
#         dst_match = re.search(r"dst_port[<=>]+([\d.]+)", condition)
#
#         proto_value = int(float(proto_match.group(1))) if proto_match else None
#         src_value = int(float(src_match.group(1))) if src_match else None
#         dst_value = int(float(dst_match.group(1))) if dst_match else None
#
#         # Map ranges to action selectors
#         if proto_value is not None:
#             if proto_value not in proto_ranges:
#                 proto_ranges[proto_value] = action_select1
#                 action_select1 += 1
#             proto_action = proto_ranges[proto_value]
#         else:
#             proto_action = 0  # Default action
#
#         if src_value is not None:
#             if src_value not in src_port_ranges:
#                 src_port_ranges[src_value] = action_select2
#                 action_select2 += 1
#             src_action = src_port_ranges[src_value]
#         else:
#             src_action = 0  # Default action
#
#         if dst_value is not None:
#             if dst_value not in dst_port_ranges:
#                 dst_port_ranges[dst_value] = action_select3
#                 action_select3 += 1
#             dst_action = dst_port_ranges[dst_value]
#         else:
#             dst_action = 0  # Default action
#
#         str1 = "simple_switch_CLI --thrift-port 9090 <<< "
#         str2 = " 1;"
#
#         # Create feature rules
#         if proto_value is not None:
#             feature1_rules.append(f"{str1}\"table_add MyIngress.feature1_exact MyIngress.set_action_select1 {proto_value:02X} => {proto_action}\"{str2}")
#         if src_value is not None:
#             feature2_rules.append(f"{str1}\"table_add MyIngress.feature2_exact MyIngress.set_action_select2 {src_value:04X} => {src_action}\"{str2}")
#         if dst_value is not None:
#             feature3_rules.append(f"{str1}\"table_add MyIngress.feature3_exact MyIngress.set_action_select3 {dst_value:04X} => {dst_action}\"{str2}")
#
#         forwarding_rules.append(
#             f"{str1}\"table_add ipv4_exact {'ipv4_forward' if action > 0 else 'drop'} "
#             f"{proto_action} {src_action} {dst_action} => {action}\"{str2}"
#         )
#
#     return feature1_rules, feature2_rules, feature3_rules, forwarding_rules

def generate_rules(ip_proto, src_port, dst_port, conditions):
    """
    Generates match-action table rules based on the decision tree.
    """

    def generate_range_rules(feature_name, value_list, max_val, action_offset):
        """
        Generates range-based rules for a feature.
        """
        if not value_list:
            return [f"simple_switch_CLI --thrift-port 9090 <<< \"table_add MyIngress.{feature_name}_exact MyIngress.set_actionselect{action_offset} 0x0->0x{max_val:X} => 1 1\""]

        rules = []
        prev_val = 0
        action = 1

        for val in sorted(value_list):
            rules.append(f"simple_switch_CLI --thrift-port 9090 <<< \"table_add MyIngress.{feature_name}_exact MyIngress.set_actionselect{action_offset} 0x{prev_val:X}->0x{val:X} => {action} 1\"")
            prev_val = val + 1
            action += 1

        rules.append(f"simple_switch_CLI --thrift-port 9090 <<< \"table_add MyIngress.{feature_name}_exact MyIngress.set_actionselect{action_offset} 0x{prev_val:X}->0x{max_val:X} => {action} 1\"")
        return rules

    feature1_rules = generate_range_rules("feature1", ip_proto, 0x20, 1)
    feature2_rules = generate_range_rules("feature2", src_port, 0xFFFF, 2)
    feature3_rules = generate_range_rules("feature3", dst_port, 0xFFFF, 3)

    forwarding_rules = []
    # Forwarding rules
    for condition, action_class in conditions:
        proto_action = src_action = dst_action = 1  # Defaults

        if "ip_proto" in condition:
            proto_match = re.search(r"ip_proto[<=>]+([\d]+)", condition)
            if proto_match:
                proto_val = int(proto_match.group(1))
                proto_action = ip_proto.index(proto_val) + 1 if proto_val in ip_proto else 1

        if "src_port" in condition:
            src_match = re.search(r"src_port[<=>]+([\d]+)", condition)
            if src_match:
                src_val = int(src_match.group(1))
                src_action = src_port.index(src_val) + 1 if src_val in src_port else 1

        if "dst_port" in condition:
            dst_match = re.search(r"dst_port[<=>]+([\d]+)", condition)
            if dst_match:
                dst_val = int(dst_match.group(1))
                dst_action = dst_port.index(dst_val) + 1 if dst_val in dst_port else 1

        forwarding_rules.append(
            f"simple_switch_CLI --thrift-port 9090 <<< \"table_add MyIngress.ipv4_exact MyIngress.ipv4_forward "
            f"{proto_action}->{proto_action} {src_action}->{src_action} {dst_action}->{dst_action} => 0x0A000102 {action_class} 1\""
        )

    return feature1_rules, feature2_rules, feature3_rules, forwarding_rules


def write_rules_script(feature1_rules, feature2_rules, feature3_rules, forwarding_rules, output_file):
    """
    Writes the rules to a shell script.
    """
    with open(output_file, 'w') as f:

        if feature1_rules:
            for rule in feature1_rules:
                f.write(rule + ";\n")
            f.write("\n")

        if feature2_rules:
            for rule in feature2_rules:
                f.write(rule + ";\n")
            f.write("\n")

        if feature3_rules:
            for rule in feature3_rules:
                f.write(rule + ";\n")
            f.write("\n")

        for rule in forwarding_rules:
            f.write(rule + ";\n")


if __name__ == "__main__":
    tree_file = "tree-four.txt"
    output_file = "rules-dt.sh"

    ip_proto, src_port, dst_port, conditions = parse_tree(tree_file)
    feature1_rules, feature2_rules, feature3_rules, forwarding_rules = generate_rules(
        ip_proto, src_port, dst_port, conditions
    )
    write_rules_script(feature1_rules, feature2_rules, feature3_rules, forwarding_rules, output_file)
    print(f"Rules script generated: {output_file}")
