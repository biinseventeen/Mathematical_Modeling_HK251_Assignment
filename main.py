import time
import argparse

from task12 import (
    parse_pnml,
    compute_reachability,
)

from task34 import (
    convert_to_indexed,
    BDDReachability,
    DeadlockDetector,
)

from task5 import ReachableOptimizer


def print_marking(marking, indexed_net):
    parts = []
    for i, p in enumerate(indexed_net.place_list):
        parts.append(f"{p}={marking[i]}")
    print("{" + ", ".join(parts) + "}")


def main():
    parser = argparse.ArgumentParser(description="Petri Net – Tasks 1–5 runner")
    parser.add_argument("pnml_file", help="Đường dẫn tới file PNML input")
    args = parser.parse_args()

    pnml_path = args.pnml_file
    print(f"=== Đọc PNML từ: {pnml_path} ===")

    # Task 1: Parse PNML
    
    net = parse_pnml(pnml_path)
    if net is None:
        print("Lỗi: Không parse được PNML.")
        return

    print(f"Số place: {len(net.places)}")
    print(f"Số transition: {len(net.transitions)}")
    print(f"Initial marking (tập place có token ban đầu): {net.initial_marking}")
    print()

    # Task 2: Explicit Reachability (BFS)
    
    print("=== Task 2: Explicit reachability (BFS) ===")
    t0 = time.time()
    visited, edges_count = compute_reachability(net)
    t1 = time.time()
    print(f"Tổng số marking khả đạt (explicit): {len(visited)}")
    print(f"Số cạnh (transition firing): {edges_count}")
    print(f"Thời gian BFS: {t1 - t0:.6f} s")
    print()

    # Chuyển sang IndexedPetriNet (cho BDD & ILP)
    
    indexed = convert_to_indexed(net)
    print("Thứ tự place trong IndexedPetriNet:")
    print(indexed.place_list)
    print()

    # Task 3: BDD Reachability

    print("=== Task 3: BDD-based reachability ===")
    bdd_reach = BDDReachability(indexed)

    t2 = time.time()
    S_bdd = bdd_reach.compute_reachable_bdd()
    reachable_markings = bdd_reach.enumerate_markings(S_bdd)
    t3 = time.time()

    print(f"Số marking khả đạt (BDD): {len(reachable_markings)}")
    print(f"Thời gian BDD reachability: {t3 - t2:.6f} s")
    print()

    # Task 4: Deadlock detection (ILP + BDD)

    print("=== Task 4: Deadlock detection (ILP + BDD) ===")
    deadlock_detector = DeadlockDetector(indexed, reachable_markings)

    t4 = time.time()
    has_deadlock, dead_marking = deadlock_detector.find_deadlock_ilp()
    t5 = time.time()

    if has_deadlock:
        print(">> Deadlock FOUND. Marking deadlock:")
        print_marking(dead_marking, indexed)
    else:
        print(">> Không tìm thấy deadlock reachable từ M0.")
    print(f"Thời gian ILP deadlock detection: {t5 - t4:.6f} s")
    print()

    # Task 5: Optimization over reachable markings

    print("=== Task 5: Optimization over reachable markings ===")

    weights = {p: 1 for p in indexed.place_list}
    print("Vector trọng số c (mặc định = 1 cho mọi place):")
    print(weights)
    print()

    optimizer = ReachableOptimizer(indexed, reachable_markings, weights)

    # ILP-based optimization
    t6 = time.time()
    found, best_marking, best_value, ilp_time = optimizer.optimize_ilp()
    t7 = time.time()

    if found:
        print(">> Marking tối ưu (ILP):")
        print_marking(best_marking, indexed)
        print(f"Giá trị c^T M (ILP) = {best_value}")
        print(f"Thời gian solver ILP (bên trong) = {ilp_time:.6f} s")
        print(f"Thời gian tổng (gọi optimize_ilp) = {t7 - t6:.6f} s")
    else:
        print(">> Không có marking nào để tối ưu (tập reachable rỗng).")
        print(f"Thời gian tổng (gọi optimize_ilp) = {t7 - t6:.6f} s")

    print()

    # (Tuỳ chọn) So sánh với version quét thường (scan) để kiểm tra chéo
    print("=== Task 5 (check): Scan all reachable markings ===")
    found2, best_marking2, best_value2, scan_time = optimizer.optimize_scan()
    if found2:
        print(">> Marking tối ưu (scan):")
        print_marking(best_marking2, indexed)
        print(f"Giá trị c^T M (scan) = {best_value2}")
        print(f"Thời gian scan: {scan_time:.6f} s")
    else:
        print(">> Không có marking nào (scan).")
    print()


if __name__ == "__main__":
    main()
