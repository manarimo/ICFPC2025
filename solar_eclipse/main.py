import argparse
from aedificium import Aedificium
from typing import List
import random
import time
import math
from collections import defaultdict


def cost(aedificium: Aedificium, assignment: List[int]) -> float:
    def tag(door):
        return assignment[door["room"]], door["door"]
    door_destinations = defaultdict(set)
    for connection in aedificium.connections:
        from_tag = tag(connection["from"])
        to_tag = tag(connection["to"])
        door_destinations[from_tag].add(to_tag)
        door_destinations[to_tag].add(from_tag)
    return sum(len(destinations) for destinations in door_destinations.values()) - len(door_destinations)


def modify(assignment: List[int]) -> List[int]:
    new_assignment = assignment[:]
    i1, i2 = random.sample(range(len(assignment)), 2)
    new_assignment[i1], new_assignment[i2] = new_assignment[i2], new_assignment[i1]
    return new_assignment


def solve(aedificium: Aedificium, duplication_factor: int) -> List[int]:
    num_rooms = len(aedificium.rooms)
    single_rooms = num_rooms // duplication_factor

    current_assignment = [i % single_rooms for i in range(num_rooms)]
    # random.shuffle(current_assignment)
    best_assignment = current_assignment[:]
    current_cost = cost(aedificium, current_assignment)
    best_cost = current_cost

    start_temp = 1e1
    end_temp = 1e-2
    duration_sec = 10
    start_time = time.time()
    while time.time() - start_time < duration_sec:
        new_assignment = modify(current_assignment)
        new_cost = cost(aedificium, new_assignment)
        temp = start_temp * (end_temp / start_temp) ** ((time.time() - start_time) / duration_sec)
        if new_cost < current_cost or random.random() < math.exp(-(new_cost - current_cost) / temp):
            current_cost = new_cost
            current_assignment = new_assignment
            if current_cost < best_cost:
                best_cost = current_cost
                best_assignment = current_assignment[:]
                print(f"best_cost: {current_cost}, temp: {temp}, time: {time.time() - start_time}")
            if best_cost == 0:
                break
    rename_map = {}
    for assignment in best_assignment:
        if assignment not in rename_map:
            rename_map[assignment] = len(rename_map)
    for i in range(len(best_assignment)):
        best_assignment[i] = rename_map[best_assignment[i]]
    return best_assignment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("aedificium_file", type=str)
    parser.add_argument("duplication_factor", type=int)

    args = parser.parse_args()
    with open(args.aedificium_file, "r") as f:
        aedificium = Aedificium.from_json(f.read())
    solution = solve(aedificium, args.duplication_factor)
    print(solution)


if __name__ == "__main__":
    main()
