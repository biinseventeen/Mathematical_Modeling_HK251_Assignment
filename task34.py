import itertools
from dd import autoref as _bdd
import pulp



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
    """
    net: PetriNet (bản bạn đã implement)
    return: IndexedPetriNet
    """
    place_list = sorted(list(net.places))  

    transitions = []
    for t in sorted(list(net.transitions)):
        pre_idx = [place_list.index(p) for p in net.pre[t]]
        post_idx = [place_list.index(p) for p in net.post[t]]
        transitions.append(IndexedTransition(pre_idx, post_idx))

    indexed = IndexedPetriNet(place_list, net.initial_marking, transitions)
    return indexed


# =====================================================================
#  Utility
# =====================================================================

def marking_to_string(m):
    return "(" + ",".join(str(x) for x in m) + ")"


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
        result = self.bdd.true
        vars_ = self.vars_prime if prime else self.vars
        for i, v in enumerate(marking):
            result &= vars_[i] if v else ~vars_[i]
        return result


    def build_transition_relation(self):
        R = self.bdd.false

        for t in self.net.transitions:
            # Enabled condition: all pre places must be 1
            cond_pre = self.bdd.true
            for p in t.pre:
                cond_pre &= self.vars[p]

            # Next state equality
            eqs = self.bdd.true
            handled = [False] * self.n

            # Places in pre → become 0
            for p in t.pre:
                eqs &= ~self.vars_prime[p]
                handled[p] = True

            # Places in post → become 1
            for p in t.post:
                eqs &= self.vars_prime[p]
                handled[p] = True

            # Others unchanged: x_i ↔ x'_i
            for i in range(self.n):
                if handled[i]: continue
                eqs &= ~(self.vars_prime[i] ^ self.vars[i])

            Rt = cond_pre & eqs
            R |= Rt

        return R


    def compute_reachable_bdd(self):
        S = self.marking_to_bdd(self.net.initMarking)

        while True:
            tmp = S & self.relR
            img = tmp.exist([v for v in self.vars])
            # rename xp -> x
            rename = {f"xp{i}": self.vars[i] for i in range(self.n)}
            img2 = img.compose(rename)
            Snew = S | img2
            if Snew == S:
                return Snew
            S = Snew


    def enumerate_markings(self, bdd_node, limit=1_000_000):
        out = []
        for assignment in bdd_node.satisfy_all():
            m = [assignment[f"x{i}"] for i in range(self.n)]
            out.append(m)
            if len(out) >= limit:
                print("[Warning] Reachability enumeration capped")
                break
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

        if nM == 0:
            return False, []

        prob = pulp.LpProblem("DeadlockCheck", pulp.LpMinimize)
        M = [pulp.LpVariable(f"M{i}", 0, 1, cat="Binary") for i in range(nP)]
        y = [pulp.LpVariable(f"y{i}", 0, 1, cat="Binary") for i in range(nM)]

        prob += 0  # objective

        prob += pulp.lpSum(y) == 1

        for p in range(nP):
            prob += M[p] == pulp.lpSum(y[i] * self.reach[i][p] for i in range(nM))

        for t in self.net.transitions:
            if len(t.pre) > 0:
                prob += pulp.lpSum(M[p] for p in t.pre) <= len(t.pre) - 1

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        if pulp.LpStatus[status] == "Optimal":
            marking = [int(M[p].value()) for p in range(nP)]
            return True, marking

        return False, []
