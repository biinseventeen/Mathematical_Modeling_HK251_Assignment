import xml.etree.ElementTree as ET
from collections import deque, defaultdict
import os

# CLASS PETRI NET
class PetriNet:
    def __init__(self):
        self.places = set()
        self.transitions = set()
        self.pre = defaultdict(set)  # Place -> Transition (Input places)
        self.post = defaultdict(set) # Transition -> Place (Output places)
        self.initial_marking = set()

    def add_place(self, p_id):
        self.places.add(p_id)

    def add_transition(self, t_id):
        self.transitions.add(t_id)

    def add_arc(self, source, target):
        # Place->Transition or Transition->Place
        if source in self.places and target in self.transitions:
            self.pre[target].add(source)
        elif source in self.transitions and target in self.places:
            self.post[source].add(target)
        else:
            print(f"Invalid arc from '{source}' to '{target}'. Nodes not found")

    def set_initial_marking(self, marking):
        self.initial_marking = set(marking)

    def get_enabled_transitions(self, current_marking):
        enabled = []
        for t in self.transitions:
            if self.pre[t].issubset(current_marking):
                enabled.append(t)
        return enabled

    def fire(self, current_marking, t):
        new_marking = set(current_marking)

        # Consume tokens
        for p in self.pre[t]:
            if p in new_marking:
                new_marking.remove(p)

        # Produce tokens
        for p in self.post[t]:
            new_marking.add(p)

        return frozenset(new_marking)

# TASK 1: PARSER (READING INPUT FILE) 
def parse_pnml(file_path):
    if not os.path.exists(file_path):
        print(f"File '{file_path}' not found.")
        return None

    tree = ET.parse(file_path)
    root = tree.getroot()
    net = PetriNet()
    
    # Helper
    def get_tag(parent, tag_name):
        found = parent.find(f"{{*}}{tag_name}")
        if found is not None: return found

        found = parent.find(tag_name)
        return found

    def find_all_tags(tag_name):
        return root.findall(f".//{{*}}{tag_name}") + root.findall(f".//{tag_name}")

    # 1. Parse Places
    for place in find_all_tags("place"):
        p_id = place.get('id')

        if p_id:
            net.add_place(p_id)
            init_tag = get_tag(place, "initialMarking")
            if init_tag is not None:
                text_tag = get_tag(init_tag, "text")
                if text_tag is not None and text_tag.text and text_tag.text.strip() == '1':
                    net.initial_marking.add(p_id)

    # 2. Parse Transitions
    for trans in find_all_tags("transition"):
        t_id = trans.get('id')
        
        if t_id:
            net.add_transition(t_id)

    # 3. Parse Arcs
    for arc in find_all_tags("arc"):
        src = arc.get('source')
        tgt = arc.get('target')
        
        if src and tgt:
            net.add_arc(src, tgt)

    return net

# TASK 2: REACHABILITY (BFS)
def compute_reachability(net):
    m0 = frozenset(net.initial_marking)
    queue = deque([m0])     
    visited = set([m0])     
    edges_count = 0         
    
    print(f"Start traversing from M0: {set(m0)}")
    
    while queue:
        curr = queue.popleft()
        enabled_ts = net.get_enabled_transitions(curr)
        
        for t in enabled_ts:
            next_m = net.fire(curr, t)
            edges_count += 1
            
            if next_m not in visited:
                visited.add(next_m)
                queue.append(next_m)
                print(f"   Fire [{t}] -> New State: {set(next_m)}")
                
    return visited, edges_count

# MAIN
if __name__ == "__main__":
    # input file
    input_file = " " 
    
    print("TASK 1: READING INPUT FILE")
    my_net = parse_pnml(input_file)
    
    if my_net:
        print(f"Parsed successfully")
        print(f"- Number of Places: {len(my_net.places)} {my_net.places}")
        print(f"- Number of Transitions: {len(my_net.transitions)} {my_net.transitions}")
        print(f"- Initial Marking: {my_net.initial_marking}") 
        
        if len(my_net.initial_marking) == 0:
            print("Initial Marking is empty. Please check the input file!")
        else:
            print("\nTASK 2: REACHABILITY")
            all_markings, total_edges = compute_reachability(my_net)
            
            print(f"\nFINAL RESULTS:")
            print(f"Total states found: {len(all_markings)}") 
            print(f"Total firing events: {total_edges}") 
