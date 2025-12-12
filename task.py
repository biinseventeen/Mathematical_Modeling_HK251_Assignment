import xml.etree.ElementTree as ET
from collections import deque, defaultdict
import os
import itertools
from dd import autoref as _bdd
import pulp
import time

# CLASS PETRI NET
class PetriNet:
    def __init__(self):
        self.places = set()
        self.transitions = set()
        self.pre = defaultdict(set)  
        self.post = defaultdict(set) 
        self.initial_marking = set()

    def add_place(self, p_id):
        self.places.add(p_id)

    def add_transition(self, t_id):
        self.transitions.add(t_id)

    def add_arc(self, source, target):
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

        for p in self.pre[t]:
            if p in new_marking:
                new_marking.remove(p)

        for p in self.post[t]:
            new_marking.add(p)

        return frozenset(new_marking)


# ----------------------------------
# TASK 1: PARSER (READING INPUT FILE)
# ----------------------------------
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


# --------------------------
# TASK 2: REACHABILITY (BFS)
# -------------------------
def compute_reachability(net):
    m0 = frozenset(net.initial_marking)
    queue = deque([m0])     
    visited = set([m0])     
    edges_count = 0         
    
    print_count = 0 
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
                if (print_count < 50):
                    print(f"   Fire [{t}] -> New State: {set(next_m)}")
                    print_count +=1
                elif (print_count == 50):
                    print("Output chỉ show 50 fires đầu tiên")
                    print_count +=1
                
    return visited, edges_count


class IndexedTransition:
    def __init__(self, pre=None, post=None):
        self.pre = pre or []
        self.post = post or []


class IndexedPetriNet:
    def __init__(self, places, init_marking, transitions):
        self.place_list = places
        self.place_to_index = {p: i for i, p in enumerate(places)}

        self.nPlaces = len(places)
        self.initMarking = [1 if places[i] in init_marking else 0
                            for i in range(self.nPlaces)]
        self.transitions = transitions


def convert_to_indexed(net):
    place_list = sorted(list(net.places))  

    transitions = []
    for t in sorted(list(net.transitions)):
        pre_idx = [place_list.index(p) for p in net.pre[t]]
        post_idx = [place_list.index(p) for p in net.post[t]]
        transitions.append(IndexedTransition(pre_idx, post_idx))

    indexed = IndexedPetriNet(place_list, net.initial_marking, transitions)
    return indexed

# =====================================================================
#  Task 3 – BDD Reachability
# =====================================================================
class BDDReachability:
    def __init__(self, net: IndexedPetriNet):
        self.net = net
        self.n = net.nPlaces

        self.bdd = _bdd.BDD()
        
       
        bdd_vars = []
        for i in range(self.n):
            bdd_vars.append(f"x{i}")   
            bdd_vars.append(f"xp{i}")  
        
        self.bdd.declare(*bdd_vars)

        self.vars = [self.bdd.var(f"x{i}") for i in range(self.n)]
        self.vars_prime = [self.bdd.var(f"xp{i}") for i in range(self.n)]

        self.identity_pairs = []
        for i in range(self.n):
            x = self.vars[i]
            xp = self.vars_prime[i]
            self.identity_pairs.append((x & xp) | (~x & ~xp))


        self.relR = self.build_transition_relation()
       

    def marking_to_bdd(self, marking, prime=False):
        expr = self.bdd.true
        vars_ = self.vars_prime if prime else self.vars
        for i, val in enumerate(marking):
            v = vars_[i]
            if val == 0:
                expr &= ~v
            else:
                expr &= v
        return expr

    def build_transition_relation(self):
        R = self.bdd.false
        
        for t in self.net.transitions:
            cond_pre = self.bdd.true
            for p in t.pre:
                cond_pre &= self.vars[p]

            affected_places = set(t.pre) | set(t.post)
            changes = self.bdd.true
            
            for p in affected_places:
                if p in t.post:
                    changes &= self.vars_prime[p] 
                elif p in t.pre:
                    changes &= ~self.vars_prime[p]

            frame = self.bdd.true
            for i in range(self.n):
                if i not in affected_places:
                    frame &= self.identity_pairs[i]

            Rt = cond_pre & changes & frame
            R |= Rt

        return R

    def compute_reachable_bdd(self):
        S = self.marking_to_bdd(self.net.initMarking)
        quant_vars = {f"x{i}" for i in range(self.n)}
        
        rename_map = {f"xp{i}": f"x{i}" for i in range(self.n)}

        iter_count = 0
        while True:
            iter_count += 1
            
            trans_potential = S & self.relR

            img_prime = self.bdd.exist(quant_vars, trans_potential)

            img = self.bdd.let(rename_map, img_prime)

            Snew = S | img

            if Snew == S:
                return Snew
            S = Snew

    def enumerate_markings(self, bdd_node, limit=100_000):
        out = []
        for model in self.bdd.pick_iter(bdd_node):
            if len(out) >= limit:
                break
            
            m = [0] * self.n
            for i in range(self.n):
                val = model.get(f"x{i}", 0)
                m[i] = int(val)
            out.append(m)
        return out


# =====================================================================
#  Task 4 – ILP Deadlock Detection
# =====================================================================

class DeadlockDetector:
    def __init__(self, net: IndexedPetriNet, reachableMarkings):
        self.net = net
        self.reach = reachableMarkings

    def find_deadlock_ilp(self):
        nP = self.net.nPlaces
        nM = len(self.reach)
        nT = len(self.net.transitions)

        if nM == 0:
            return False, []

        prob = pulp.LpProblem("DeadlockCheck", pulp.LpMinimize)
        
        # Decision variables
        M = [pulp.LpVariable(f"M{i}", 0, 1, cat="Binary") for i in range(nP)]
        y = [pulp.LpVariable(f"y{i}", 0, 1, cat="Binary") for i in range(nM)]
        
        z = [pulp.LpVariable(f"z{t}", 0, 1, cat="Binary") for t in range(nT)]

        prob += 0  

        prob += pulp.lpSum(y) == 1

        for p in range(nP):
            prob += M[p] == pulp.lpSum(y[i] * self.reach[i][p] for i in range(nM))

        
        for t_idx, t in enumerate(self.net.transitions):
            if len(t.pre) == 0:
                prob += z[t_idx] == 1
            else:
                
                
                token_sum = pulp.lpSum(M[p] for p in t.pre)
                K = len(t.pre)
                
                
                prob += token_sum >= K * z[t_idx]
                prob += token_sum <= K - 1 + K * z[t_idx]

        prob += pulp.lpSum(z) == 0

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if pulp.LpStatus[status] == "Optimal":
            marking = [int(round(M[p].value())) for p in range(nP)]
            return True, marking

        return False, []


# =====================================================================
#  Task 5 - Reachable Optimization
# =====================================================================
class ReachableOptimizer:
    def __init__(self, net, reachableMarkings, weights):
        self.net = net
        self.reach = reachableMarkings

        self.w = [0] * net.nPlaces
        for i, p in enumerate(net.place_list):
            if p in weights:
                self.w[i] = weights[p]

    def optimize_ilp(self):
        nP = self.net.nPlaces
        nM = len(self.reach)

        start = time.time()

        if nM == 0:
            end = time.time()
            return False, [], None, end - start

        prob = pulp.LpProblem("ReachableOptimization", pulp.LpMaximize)

        M = [pulp.LpVariable(f"M{p}", 0, 1, cat="Binary") for p in range(nP)]
        y = [pulp.LpVariable(f"y{i}", 0, 1, cat="Binary") for i in range(nM)]

        prob += pulp.lpSum(self.w[p] * M[p] for p in range(nP))

        prob += pulp.lpSum(y) == 1

        for p in range(nP):
            prob += M[p] == pulp.lpSum(y[i] * self.reach[i][p] for i in range(nM))

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))

        end = time.time()
        running_time = end - start

        if pulp.LpStatus[status] == "Optimal":
            best_marking = [int(round(M[p].value())) for p in range(nP)]
            best_value = sum(self.w[p] * best_marking[p] for p in range(nP))
            return True, best_marking, best_value, running_time

        return False, [], None, running_time

    def optimize_scan(self):
        nP = self.net.nPlaces
        nM = len(self.reach)

        start = time.time()

        if nM == 0:
            end = time.time()
            return False, [], None, end - start

        best_marking = None
        best_value = None

        for m in self.reach:
            value = 0
            for p in range(nP):
                value += self.w[p] * m[p]

            if best_value is None or value > best_value:
                best_value = value
                best_marking = m

        end = time.time()
        running_time = end - start
        return True, best_marking, best_value, running_time