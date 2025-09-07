from random import Random
import itertools
from collections import defaultdict
from pathlib import Path
import time
import json

from aedificium import build_connections, Aedificium, problem_names
import api


def solve(single_rooms: int, duplication_factor: int, client: api.APIClient) -> Aedificium:
    num_rooms = single_rooms * duplication_factor
    aedificium = solve_single(single_rooms, client)
    if duplication_factor > 1:
        print("not implemented")
        return None
    return aedificium


def solve_single(num_rooms: int, client: api.APIClient) -> Aedificium:
    random_seed = None
    hash_length = 6
    hash_count = 4
    first_steps = 6
  
    random = Random(random_seed)

    vertex_hasher_plans = [
        ''.join(random.choices("012345", k=hash_length)) for _ in range(hash_count)
    ]

    plans = []
    metadata = []
    for first_length in range(first_steps):
        for first_path in itertools.product("012345", repeat=first_length):
            first_plan = ''.join(first_path)
            for vertex_hasher_plan in vertex_hasher_plans:
                plan = first_plan + vertex_hasher_plan
                plans.append(plan)
                metadata.append((first_length, vertex_hasher_plan))

    print(f"{len(plans)} plans")
    res = client.explore(plans)

    path_hashes = defaultdict(dict)
    for plan, (path_length, vertex_hasher_plan), result in zip(plans, metadata, res["results"]):
        path = plan[:path_length]
        vertex_hash = tuple(result[path_length + 1:])
        path_hashes[path][vertex_hasher_plan] = vertex_hash

    def freeze(hashes):
        sorted_hashes = []
        for key in sorted(hashes.keys()):
            sorted_hashes.append(hashes[key])
        return tuple(sorted_hashes)

    path_hashes = {k: freeze(v) for k, v in path_hashes.items()}
    unique_vertex_hashes = set(path_hashes.values())
    if len(unique_vertex_hashes) < num_rooms:
        print(f"not enough vertex hashes: {len(unique_vertex_hashes)} < {num_rooms}")
        return
    vertex_indexes = {v: i for i, v in enumerate(unique_vertex_hashes)}
    path_results = {k: vertex_indexes[v] for k, v in path_hashes.items()}

    starting_room = path_results['']
    print(f"starting room: {starting_room}")
    rooms = [None] * num_rooms
    for plan, (path_length, vertex_hasher_plan), result in zip(plans, metadata, res["results"]):
        path = plan[:path_length]
        current_room = path_results[path]
        current_room_label = result[path_length]
        if rooms[current_room] is None:
            rooms[current_room] = current_room_label
        elif rooms[current_room] != current_room_label:
            print(f"conflict: {current_room}, {current_room_label}, {rooms[current_room]}")
            return
    if any(room is None for room in rooms):
        print(f"not enough room info: {rooms}")
        return
    print(f"rooms: {rooms}")

    door_destinations = {}
    for path, result in path_results.items():
        if len(path) < 1:
            continue
        prev_room = path_results[path[:-1]]
        last_door = int(path[-1])
        next_room = result
        last_door = (prev_room, last_door)
        if last_door not in door_destinations:
            door_destinations[last_door] = next_room
        elif door_destinations[last_door] != next_room:
            print(f"conflict: {last_door}, {next_room}, {door_destinations[last_door]}")
            return
    if len(door_destinations) != num_rooms * 6:
        print(f"not enough door destinations: {len(door_destinations)} != {num_rooms * 6}")
        return

    connections = build_connections(door_destinations, num_rooms)
    if connections is None:
        print(f"failed to build connections: {door_destinations}")
        return

    aedificium = Aedificium(rooms, starting_room, connections)
    return aedificium


def main():
    client = api.APIClient(
        api_base="http://localhost:8000",
        api_id="vertrages",
    )
    # client = api.APIClient(
    #     api_base="https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com",
    #     api_id="amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ",
    # )

    problem_name = "quintus"
    # problem_name = "random_full_6_2_42"
    if problem_name in problem_names():
        single_rooms, duplication_factor = problem_names()[problem_name]
    else:
        single_rooms = 6
        duplication_factor = 2
    client.select(problem_name)
    aedificium = solve(single_rooms, duplication_factor, client)
    if aedificium is None:
        print("failed to solve")
        return
    judge_result = client.guess(aedificium.to_dict())
    print(f"judge_result: {judge_result}")
    if not judge_result["correct"]:
        print("failed to guess")
        return
    if client.api_base != "https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com":
        return
    print("official remote server was used. saving our guess...")
    path = Path(__file__).parent / "official_aedificiums" / problem_name / f"{int(time.time() * 10 ** 6)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(aedificium.to_dict(), f)


if __name__ == "__main__":
    main()
