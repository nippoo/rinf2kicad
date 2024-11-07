import sys
import time
from datetime import datetime

# Constants
NAMELEN = 128
PINSMAX = 512
NETSMAX = 1024
COMPMAX = 1024

class Pin:
    def __init__(self, name='', alias='', pintype='passive'):
        self.name = name
        self.alias = alias
        self.pintype = pintype

class Component:
    def __init__(self, name='', label='', footprint='', max_pins=0):
        self.name = name
        self.label = label
        self.footprint = footprint
        self.max_pins = max_pins
        self.pins = [Pin() for _ in range(PINSMAX)]

class Net:
    def __init__(self, name=''):
        self.name = name

component_table = [Component() for _ in range(COMPMAX)]
net_table = [Net() for _ in range(NETSMAX)]

def extract_token(buffer, start_pos, delimiter='"'):
    """Extracts a token enclosed by a specified delimiter starting from a position."""
    start = buffer.find(delimiter, start_pos) + 1
    end = buffer.find(delimiter, start)
    return buffer[start:end]

def get_net_names(buffer, net_table):
    found_nets = 0
    pointer = 0
    while pointer < len(buffer) and found_nets < NETSMAX:
        pos = buffer.find(".ADD_TER", pointer)
        if pos == -1:
            break
        pos += len(".ADD_TER")

        end_pos = buffer.find(".ADD_TER", pos)
        if (end_pos == -1):
            end_pos = buffer.find(".END", pos)
        if (end_pos == -1):
            break

        # Extract the net name from the .ADD_TER line
        net_name = extract_token(buffer, pos)
        net_table[found_nets].name = net_name

        # Initialize a list to collect pins for the current net
        net_pins = []

        # Process lines under the current .ADD_TER block
        while True:
            # Read the line, ignoring the ".TER" keyword if present
            line = buffer[pos:].splitlines()[0]
            parts = line.lstrip(".TER").split()

            # Ensure we only extract valid component and pin information
            if len(parts) >= 2:
                component_name = parts[0]
                pin_number = parts[1]


                # Append this pin as a tuple (component_name, pin_number, pintype) to net_pins
                net_pins.append((component_name, pin_number, "passive"))

            pos += len(line) + 1  # Move position to the next line

            if (pos >= end_pos) or (len(line) == 0):
                break

        # Store the collected pins in the current net
        net_table[found_nets].pins = net_pins
        found_nets += 1
        pointer = pos

        # print(f"Net: {net_name}, Pins: {net_pins}")

    return found_nets

def get_component_names(buffer, component_table):
    found_components = 0
    pointer = 0
    while pointer < len(buffer) and found_components < COMPMAX:
        pos = buffer.find(".ADD_COM", pointer)
        if pos == -1:
            break
        pos += len(".ADD_COM") + 1

        # Split the line to get relevant parts
        line = buffer[pos:].splitlines()[0].strip()
        parts = line.split('"')
        
        if len(parts) >= 4:
            # Extract the component name, label, and footprint correctly
            comp_name = parts[0].strip().split()[0]
            comp_label = parts[1]
            comp_footprint = parts[3]
            
            component_table[found_components] = Component(comp_name, comp_label, comp_footprint)
            found_components += 1
        
        pointer = pos
    return found_components

def write_header(destination, source_filename):
    destination.write(f"(export (version D)\n"
                      f"  (design\n"
                      f"    (source \"{source_filename}\")\n"
                      f"    (date \"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\")\n"
                      f"    (tool \"rinf2kicad\")\n"
                      f"  )\n")

def write_components(destination, num_components):
    destination.write("  (components\n")
    for component in component_table[:num_components]:
        destination.write(f"    (comp (ref {component.name})\n"
                          f"      (value \"{component.label}\")\n"
                          f"      (footprint \"{component.footprint}\")\n"
                          f"      (sheetpath (names /) (tstamps /))\n"
                          f"      (tstamp {int(time.time())}))\n")
    destination.write("  )\n")

def write_nets(destination, num_nets, num_components):
    destination.write("  (nets\n")
    for net_index in range(num_nets):
        net_name = net_table[net_index].name
        destination.write(f"    (net (code \"{net_index + 1}\") (name \"{net_name}\")\n")
        
        for component_name, pin_alias, pintype in net_table[net_index].pins:
            destination.write(f"      (node (ref \"{component_name}\") (pin \"{pin_alias}\") (pintype \"{pintype}\"))\n")
        
        destination.write("    )\n")
    destination.write("  )\n")

def main():
    if len(sys.argv) != 3:
        print("Usage:\n\tpython rinf2kicad.py input_file output_file")
        return

    source_filename = sys.argv[1]
    dest_filename = sys.argv[2]

    try:
        with open(source_filename, "rb") as source:
            buffer = source.read().decode(errors='ignore')
    except IOError:
        print(f"Couldn't open: {source_filename}")
        return

    try:
        with open(dest_filename, "w") as destination:
            write_header(destination, source_filename)
            
            num_components = get_component_names(buffer, component_table)
            num_nets = get_net_names(buffer, net_table)
            print(f"{num_components} components found\n{num_nets} nets found\n")

            write_components(destination, num_components)
            write_nets(destination, num_nets, num_components)
            destination.write("))\n")
    except IOError:
        print(f"Couldn't open: {dest_filename}")

if __name__ == "__main__":
    main()