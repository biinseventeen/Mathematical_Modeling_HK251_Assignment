# Petri Net Analysis & Optimization Tool

A comprehensive Python tool designed to parse, analyze, and optimize Petri Nets using PNML (Petri Net Markup Language) files. This project compares explicit state traversal algorithms against symbolic methods (BDD) and utilizes Integer Linear Programming (ILP) for deadlock detection and optimization.

## Features

The application executes five distinct analysis tasks:

1.  **PNML Parsing**: Extracts places, transitions, arcs, and initial markings from standard `.pnml` files.
2.  **Explicit Reachability (BFS)**: Traverses the state space using Breadth-First Search to count reachable markings and transition firings. Output is rate-limited to the first 50 firings to prevent console flooding.
3.  **Symbolic Reachability (BDD)**: Utilizes Binary Decision Diagrams (via the `dd` library) to efficiently handle state explosion and calculate reachable sets for complex nets.
4.  **Deadlock Detection**: Combines reachability data with ILP (using `pulp`) to mathematically prove the existence of deadlock states reachable from the initial marking.
5.  **Reachable Optimization**: Assigns random weights to places and solves an optimization problem to find the marking that maximizes the weighted sum ($c^T M$). It compares the ILP solver result against a linear scan of all markings for validation.

## Prerequisites

Ensure you have Python 3 installed. You will need to install the following dependencies for BDDs and Linear Programming:

```bash
pip install dd pulp
```

## Project Structures

The project consists of 2 main Python files: a `task.py` file which contains the core logic classes, and a `main.py` file which is the entry point, handling argument parsing, timing execution, and coordinating the 5 tasks.

## Usage:

Run the `main.py` script and pass the path to a PNML file as an argument:

```bash
python main.py test_005.pnml
```

**Expected Output**

The script will output:

1. Network statistics (Places/Transitions).
2. BFS traversal results (Explicit count).
3. BDD reachability count (Symbolic count).
4. Deadlock detection results.
5. Optimization results (ILP vs. Linear Scan).

## Testcases
There are 7 testcases in total, arranged in order of increasing complexity:
- `test_001.pnml`: A trivial net with 1 place and no transitions.
- `test_002.pnml`: Demonstrates a "Simple Fork - Split Pattern".
- `test_003.pnml`: Represents a "Simple Cycle" topology.
- `test_004.pnml`: A "Fork-join with Synchronisation" pattern.
- `test_005.pnml`: A complex net that can cause a deadlock if the wrong sequence is chosen.
- `test_006.pnml`: A test case to demonstrate that a self-loop does not count as a deadlock/error.
- `test_007.pnml`: A "State Explosion" test case designed to prove BDDs are more effective than BFS for large state spaces.


## AND HAPPY CODING!
