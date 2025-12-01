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
        self.pre = defaultdict(set)  # Transition -> Set of input places
        self.post = defaultdict(set) # Transition -> Set of output places
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

        # Consume tokens from input places
        for p in self.pre[t]:
            if p in new_marking:
                new_marking.remove(p)

        # Produce tokens in output places
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

        self.bdd.declare(*[f"x{i}" for i in range(self.n)])
        self.bdd.declare(*[f"xp{i}" for i in range(self.n)])

        self.vars = [self.bdd.var(f"x{i}") for i in range(self.n)]
        self.vars_prime = [self.bdd.var(f"xp{i}") for i in range(self.n)]

        self.relR = self.build_transition_relation()

    def marking_to_bdd(self, marking, prime=False):
        """
        Convert marking (list of 0/1) to BDD
        prime=False: use variables x_i
        prime=True: use variables xp_i
        """
        result = self.bdd.true
        vars_ = self.vars_prime if prime else self.vars
        for i, v in enumerate(marking):
            if v:
                result &= vars_[i]
            else:
                result &= ~vars_[i]
        return result

    def build_transition_relation(self):
        R = self.bdd.false

        for t in self.net.transitions:
            cond_pre = self.bdd.true
            for p in t.pre:
                cond_pre &= self.vars[p]

            eqs = self.bdd.true
            handled = [False] * self.n

            for p in t.pre:
                eqs &= ~self.vars_prime[p]
                handled[p] = True

            for p in t.post:
                eqs &= self.vars_prime[p]
                handled[p] = True

            for i in range(self.n):
                if handled[i]:
                    continue
                x  = self.vars[i]
                xp = self.vars_prime[i]
                eqs &= ((~xp | x) & (~x | xp))

            Rt = cond_pre & eqs
            R |= Rt

        return R

    def compute_reachable_bdd(self):
        """
        Compute reachable markings as BDD:
        S_{k+1}(x) = S_k(x) ∪ Post(S_k)(x)
                   = S_k(x) ∪ ∃x. ( S_k(x) ∧ R(x,x') )[x'→x]
        """
        S = self.marking_to_bdd(self.net.initMarking)

        quant_vars = {f"x{i}" for i in range(self.n)}

        while True:
            tmp = S & self.relR

            img = self.bdd.exist(quant_vars, tmp)

            
            rename = {f"xp{i}": f"x{i}" for i in range(self.n)}
            img2 = self.bdd.let(rename, img)

            Snew = S | img2

            if Snew == S:
                return Snew

            S = Snew

    def enumerate_markings(self, bdd_node, limit=1_000_000):
        """
        Enumerate markings satisfying the BDD node (as list of 0/1).
        Use self.bdd.pick(...) to iteratively extract solutions.
        """
        out = []
        u = bdd_node

        while u != self.bdd.false and len(out) < limit:
            model = self.bdd.pick(u)
            if model is None:
                break

            m = [model.get(f"x{i}", 0) for i in range(self.n)]
            out.append(m)

            cube = self.bdd.true
            for i in range(self.n):
                var_name = f"x{i}"
                val = model.get(var_name, 0)
                v = self.bdd.var(var_name)
                cube &= v if val else ~v

            u = u & ~cube

        if len(out) >= limit:
            print("[Warning] Reachability enumeration capped")

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