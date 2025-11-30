# check_outputs.py
"""
Script kiểm tra Tasks 3, 4, 5 trên 3 mô hình PNML:
- easy_deadlock.pnml
- fork_two_tokens.pnml
- loop_and_deadlock.pnml

Mỗi test sẽ:
- Dùng BDDReachability (Task 3) để lấy reachable markings
- Dùng DeadlockDetector (Task 4) để tìm deadlock
- Dùng ReachableOptimizer (Task 5) để tối ưu hàm mục tiêu c^T M
"""

from task12 import parse_pnml
from task34 import convert_to_indexed, BDDReachability, DeadlockDetector
from task5 import ReachableOptimizer


def test_easy_deadlock():
    print("=== TEST 1: easy_deadlock.pnml ===")
    net = parse_pnml("easy_deadlock.pnml")
    if net is None:
        print("parse_pnml trả về None -> FAIL")
        return

    indexed = convert_to_indexed(net)
    bdd = BDDReachability(indexed)

    # Task 3: BDD reachability
    S = bdd.compute_reachable_bdd()
    reach = bdd.enumerate_markings(S)
    print(f"[T3] Reachable markings (BDD): {reach}")

    ok_reach = (len(reach) == 1 and reach[0] == [1])
    print(f"  -> Expect 1 marking = [1]  --> {'PASS' if ok_reach else 'FAIL'}")

    # Task 4: Deadlock detection
    detector = DeadlockDetector(indexed, reach)
    has_dead, dead = detector.find_deadlock_ilp()
    expected_dead = [1]
    ok_dead = has_dead and dead == expected_dead
    print(f"[T4] Deadlock: has_dead={has_dead}, marking={dead}, expect={expected_dead}")
    print(f"  -> {'PASS' if ok_dead else 'FAIL'}")

    # Task 5: Optimization (c(p0) = 1)
    weights = {p: 1 for p in indexed.place_list}
    opt = ReachableOptimizer(indexed, reach, weights)
    found, best_mark, best_val, _ = opt.optimize_ilp()
    ok_opt = found and best_mark == [1] and best_val == 1
    print(f"[T5] Optimization: found={found}, best_mark={best_mark}, best_val={best_val}, expect [1], 1")
    print(f"  -> {'PASS' if ok_opt else 'FAIL'}")
    print()


def test_fork_two_tokens():
    print("=== TEST 2: fork_two_tokens.pnml ===")
    net = parse_pnml("fork_two_tokens.pnml")
    if net is None:
        print("parse_pnml trả về None -> FAIL")
        return

    indexed = convert_to_indexed(net)
    bdd = BDDReachability(indexed)

    # Task 3: BDD reachability
    S = bdd.compute_reachable_bdd()
    reach = bdd.enumerate_markings(S)
    print(f"Place list: {indexed.place_list}")
    print(f"[T3] Reachable markings (BDD): {reach}")

    # Với places sorted = ['p0','p1','p2']:
    # M0  = [1,0,0]
    # M1  = [0,1,1]
    expected_reach = [[1, 0, 0], [0, 1, 1]]
    ok_reach = (len(reach) == 2 and sorted(reach) == sorted(expected_reach))
    print(f"  -> Expect markings {expected_reach}  --> {'PASS' if ok_reach else 'FAIL'}")

    # Task 4: Deadlock detection -> deadlock = [0,1,1]
    detector = DeadlockDetector(indexed, reach)
    has_dead, dead = detector.find_deadlock_ilp()
    expected_dead = [0, 1, 1]
    ok_dead = has_dead and dead == expected_dead
    print(f"[T4] Deadlock: has_dead={has_dead}, marking={dead}, expect={expected_dead}")
    print(f"  -> {'PASS' if ok_dead else 'FAIL'}")

    # Task 5: Optimization, weights = 1 -> best = [0,1,1], value = 2
    weights = {p: 1 for p in indexed.place_list}
    opt = ReachableOptimizer(indexed, reach, weights)
    found, best_mark, best_val, _ = opt.optimize_ilp()
    ok_opt = found and best_mark == [0, 1, 1] and best_val == 2
    print(f"[T5] Optimization: found={found}, best_mark={best_mark}, best_val={best_val}, expect [0,1,1], 2")
    print(f"  -> {'PASS' if ok_opt else 'FAIL'}")
    print()


def test_loop_and_deadlock():
    print("=== TEST 3: loop_and_deadlock.pnml ===")
    net = parse_pnml("loop_and_deadlock.pnml")
    if net is None:
        print("parse_pnml trả về None -> FAIL")
        return

    indexed = convert_to_indexed(net)
    bdd = BDDReachability(indexed)

    # Task 3: BDD reachability
    S = bdd.compute_reachable_bdd()
    reach = bdd.enumerate_markings(S)
    print(f"Place list: {indexed.place_list}")
    print(f"[T3] Reachable markings (BDD): {reach}")

    # M0 = [1,0,0] (p0)
    # M1 = [0,1,0] (p1)
    # M2 = [0,0,1] (p2)
    ok_reach = (len(reach) == 3)
    print(f"  -> Expect 3 markings  --> {'PASS' if ok_reach else 'FAIL'}")

    # Task 4: Deadlock detection -> deadlock = [0,0,1] (p2)
    detector = DeadlockDetector(indexed, reach)
    has_dead, dead = detector.find_deadlock_ilp()
    expected_dead = [0, 0, 1]
    ok_dead = has_dead and dead == expected_dead
    print(f"[T4] Deadlock: has_dead={has_dead}, marking={dead}, expect={expected_dead}")
    print(f"  -> {'PASS' if ok_dead else 'FAIL'}")

    # Task 5: Optimization
    # Với weights=1 cho mọi place, mỗi marking có 1 token -> value tối ưu = 1
    # Marking tối ưu có thể là bất kỳ marking reachable.
    weights = {p: 1 for p in indexed.place_list}
    opt = ReachableOptimizer(indexed, reach, weights)
    found, best_mark, best_val, _ = opt.optimize_ilp()
    reachable_set = set(tuple(m) for m in reach)
    ok_opt = found and best_val == 1 and tuple(best_mark) in reachable_set
    print(f"[T5] Optimization: found={found}, best_mark={best_mark}, best_val={best_val}, expect value=1 & marking ∈ reachable")
    print(f"  -> {'PASS' if ok_opt else 'FAIL'}")
    print()


def main():
    test_easy_deadlock()
    test_fork_two_tokens()
    test_loop_and_deadlock()


if __name__ == "__main__":
    main()
