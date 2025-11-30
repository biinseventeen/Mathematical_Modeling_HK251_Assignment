import time
import pulp


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
            best_marking = [int(M[p].value()) for p in range(nP)]
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
