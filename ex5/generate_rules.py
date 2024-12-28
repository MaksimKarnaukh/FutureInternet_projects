import re

fields = ["ip_proto", "src_port", "dst_port"]
# fields = ["proto", "src", "dst"] # for the lecture demo and their tree file, uncomment this

def parse_tree(tree_file):
    """
    Parses the decision tree file and extracts ranges tables, conditions and actions.
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
                if "proto" in line and match:
                    ip_proto = eval(match.group(1))
                elif "src" in line and match:
                    src_port = eval(match.group(1))
                elif "dst" in line and match:
                    dst_port = eval(match.group(1))
        except Exception as e:
            print(f"Error parsing line: {line}\n{e}")

    return ip_proto, src_port, dst_port, conditions

def extract_range(condition, field, value_list, max_val):
    """
    Extracts the min and max range for a field in a condition based on condition field inequalities.
    """
    matches = re.findall(rf"{field}([<>=!]+)(\d+)", condition)
    min_range = 0
    max_range = max_val

    for operator, value in matches:
        value = int(value)
        if operator in ("<", "<="):
            max_range = min(max_range, value - 1 if operator == "<" else value)
        elif operator in (">", ">="):
            min_range = max(min_range, value + 1 if operator == ">" else value)
        elif operator == "=":
            min_range = max(min_range, value)
            max_range = min(max_range, value)

    # map the extracted range to action select range indices
    start_action = 1
    end_action = 1

    for i, val in enumerate(sorted(value_list + [max_val])):
        if min_range <= val:
            start_action = i + 1
            break
    for i, val in enumerate(sorted(value_list + [max_val])):
        if max_range <= val:
            end_action = i + 1
            break

    return start_action, end_action

def class_to_action(class_, class_to_action_map):
    """
    Maps a class to an action.
    """
    try:
        return class_to_action_map[class_]
    except KeyError:
        print(f"Class {class_} not found")

def action_to_host_port(action, action_to_host_port_map):
    """
    Maps an action to a host port.
    """
    try:
        host_port = action_to_host_port_map[action]
        if not host_port: # drop, but how? whatever just raise KeyError ¯\_(ツ)_/¯
            raise KeyError
        return host_port
    except KeyError:
        print(f"Action {action} not found")

def get_dst_host_ip_port_string(class_, class_to_action_map, action_to_host_port_map):
    """
    Returns the destination host IP and port for a given class.
    """
    action = class_to_action(class_, class_to_action_map)
    host, port = action_to_host_port(action, action_to_host_port_map)
    host_in_hex = f"0x0A00010{host:X}"
    return f"{host_in_hex} {port}"

def generate_rules(ip_proto, src_port, dst_port, conditions, class_to_action_map, action_to_host_port_map):
    """
    Generates rules for shell script based on the decision tree.
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
    for condition, action_class in conditions:
        proto_action_start, proto_action_end = extract_range(condition, fields[0], ip_proto, 0x20)
        src_action_start, src_action_end = extract_range(condition, fields[1], src_port, 0xFFFF)
        dst_action_start, dst_action_end = extract_range(condition, fields[2], dst_port, 0xFFFF)

        forwarding_rules.append(
            f"simple_switch_CLI --thrift-port 9090 <<< \"table_add MyIngress.ipv4_exact MyIngress.ipv4_forward "
            f"{proto_action_start}->{proto_action_end} {src_action_start}->{src_action_end} {dst_action_start}->{dst_action_end} => {get_dst_host_ip_port_string(action_class, class_to_action_map, action_to_host_port_map)} 1\""
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

    """Class matching guide (see https://github.com/grupogita/ONOSP4-tutorial/blob/main/DecisionTrees2/README.md):"""
    # Maps class to action
    class_to_action_map = {
        0: 2,
        1: 3,
        2: 2,
        3: 3,
        4: 4,
    }
    # Maps action to host and port
    action_to_host_port_map = {
        0: (), # drop
        2: (2, 2),
        3: (3, 3),
        4: (4, 4),
    }

    ip_proto, src_port, dst_port, conditions = parse_tree(tree_file)
    feature1_rules, feature2_rules, feature3_rules, forwarding_rules = generate_rules(ip_proto, src_port, dst_port, conditions, class_to_action_map, action_to_host_port_map)
    write_rules_script(feature1_rules, feature2_rules, feature3_rules, forwarding_rules, output_file)
    print(f"Rules script generated: {output_file}")
