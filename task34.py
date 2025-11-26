import itertools
from dd import autoref as _bdd  # pure Python BDD
import pulp

# -------------------------------

# Petri net simple representation

# -------------------------------

class Transition:
    def __init__(self, pre=None, post=None):
        self.pre = pre or []
        self.post = post or []

class PetriNet:
    def __init__(self, nPlaces=0, initMarking=None, transitions=None):
        self.nPlaces = nPlaces
        self.initMarking = initMarking or [0]*nPlaces
        self.transitions = transitions or []

# -------------------------------

# Utility: print marking

# -------------------------------

def marking_to_string(m):
    return "(" + ",".join(str(x) for x in m) + ")"

# -------------------------------

# Task 3: BDD-based reachable set

# -------------------------------

class BDDReachability:
    def __init__(self, net: PetriNet):
        self.net = net
        self.n = net.nPlaces
        self.bdd = _bdd.BDD()
        self.vars = [self.bdd.var(f'x{i}') for i in range(self.n)]
        self.vars_prime = [self.bdd.var(f'xp{i}') for i in range(self.n)]
        self.relR = self.build_transition_relation()


def marking_to_bdd(self, marking, prime=False):
    res = self.bdd.true
    vars_ = self.vars_prime if prime else self.vars
    for i, val in enumerate(marking):
        res &= vars_[i] if val else ~vars_[i]
    return res

def build_transition_relation(self):
    R = self.bdd.false
    for t in self.net.transitions:
        cond_pre = self.bdd.true
        for p in t.pre:
            cond_pre &= self.vars[p]
        eqs = self.bdd.true
        handled = [False]*self.n
        for p in t.pre:
            eqs &= ~self.vars_prime[p]
            handled[p] = True
        for p in t.post:
            eqs &= self.vars_prime[p]
            handled[p] = True
        for i in range(self.n):
            if handled[i]: continue
            # x'_i <-> x_i
            eqs &= ~(self.vars_prime[i] ^ self.vars[i])
        Rt = cond_pre & eqs
        R |= Rt
    return R

def compute_reachable_bdd(self):
    S = self.marking_to_bdd(self.net.initMarking)
    while True:
        tmp = S & self.relR
        # existential quantification over unprimed variables
        img = tmp.exist([v for v in self.vars])
        # rename primed -> unprimed: map xp_i -> x_i
        img_renamed = img.compose({f'xp{i}': self.vars[i] for i in range(self.n)})
        Snew = S | img_renamed
        if Snew == S:
            return Snew
        S = Snew

# enumerate markings from BDD
def enumerate_markings(self, bdd, cap=1000000):
    out = []
    for assignment in bdd.satisfy_all():
        m = [assignment[f'x{i}'] for i in range(self.n)]
        out.append(m)
        if len(out) >= cap:
            print(f"[Warning] reachability enumeration capped at {cap} states")
            break
    return out


# -------------------------------

# Task 4: Deadlock detection using ILP (PuLP)

# -------------------------------

class DeadlockDetector:
    def __init__(self, net: PetriNet, reachableMarkings):
        self.net = net
        self.reach = reachableMarkings


def find_deadlock_ilp(self):
    nPlaces = self.net.nPlaces
    nMarks = len(self.reach)
    if nMarks == 0:
        return False, []

    prob = pulp.LpProblem("DeadlockCheck", pulp.LpMinimize)

    # variables M_p for places, y_i for reachable markings
    M = [pulp.LpVariable(f'M{p}', 0, 1, cat='Binary') for p in range(nPlaces)]
    y = [pulp.LpVariable(f'y{i}', 0, 1, cat='Binary') for i in range(nMarks)]

    # objective irrelevant
    prob += 0

    # constraint: select exactly one reachable marking
    prob += pulp.lpSum(y) == 1

    # M_p = sum_i y_i * reach[i][p]
    for p in range(nPlaces):
        prob += M[p] == pulp.lpSum(y[i]*self.reach[i][p] for i in range(nMarks))

    # deadlock constraints: each transition disabled
    for t in self.net.transitions:
        if t.pre:
            prob += pulp.lpSum(M[p] for p in t.pre) <= len(t.pre) - 1

    # solve
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    if pulp.LpStatus[status] == "Optimal":
        outMarking = [int(M[p].value()) for p in range(nPlaces)]
        return True, outMarking
    return False, []





