from aedificium import Aedificium, problem_names
import api
import random
from typing import List

import z3


def solve(num_rooms: int, plans: List[str], results: List[str]):
    s = z3.Solver()
    m = len(plans)

    # room history
    xs = [[z3.Int(f"x_{plan_index}_{i}") for i in range(len(results[plan_index]))] for plan_index in range(m)]
    for single_xs, result in zip(xs, results):
        for x, r in zip(single_xs, result):
            s.add(x >= 0)
            s.add(x < num_rooms)
            s.add(x % 4 == int(r))

    starting_room = z3.Int(f"starting_room")
    for plan_index in range(m):
        s.add(xs[plan_index][0] == starting_room)

    # door destination function
    dd = z3.Function("dd", z3.IntSort(), z3.IntSort(), z3.IntSort())
    # door connection function
    dc = z3.Function("dc", z3.IntSort(), z3.IntSort(), z3.IntSort())
    for room_id in range(num_rooms):
        for door_id in range(6):
            s.add(dd(room_id, door_id) >= 0)
            s.add(dd(room_id, door_id) < num_rooms)

            s.add(dc(room_id, door_id) >= 0)
            s.add(dc(room_id, door_id) < 6)

            s.add(dd(dd(room_id, door_id), dc(room_id, door_id)) == room_id)
            s.add(dc(dd(room_id, door_id), dc(room_id, door_id)) == door_id)

    for plan_index in range(m):
        single_xs = xs[plan_index]
        single_plan = plans[plan_index]
        for x_fr, door, x_to in zip(single_xs[:-1], single_plan, single_xs[1:]):
            s.add(dd(x_fr, int(door)) == x_to)

    if s.check() != z3.sat:
        print("failed to solve")
        return

    rooms = [i % 4 for i in range(num_rooms)]
    starting_room = s.model().eval(starting_room).as_long()
    used_doors = set()
    connections = []
    for i in range(num_rooms):
        for door_id in range(6):
            door = (i, door_id)
            if door in used_doors:
                continue
            room_to = s.model().eval(dd(i, door_id)).as_long()
            door_to = s.model().eval(dc(i, door_id)).as_long()
            to = room_to, door_to
            if to in used_doors:
                print(f"DEBUG: door {door} is used in different connection. contradiction")
                return
            used_doors.add(door)
            used_doors.add(to)
            connections.append({
                "from": {"room": i, "door": door_id},
                "to": {"room": room_to, "door": door_to}
            })
    return Aedificium(rooms, starting_room, connections)


def main():
    client = api.APIClient(
        api_base="http://localhost:8000",
        api_id="sakazuki",
    )
    # client = api.APIClient(
    #     api_base="https://31pwr5t6ij.execute-api.eu-west-2.amazonaws.com",
    #     api_id="amylase.inquiry@gmail.com X6G0RVKUlX20I8XSUsnkIQ",
    # )

    # problem_name = "primus"
    problem_name = "random_full_12_1_42"
    if problem_name in problem_names():
        single_rooms, duplication_factor = problem_names()[problem_name]
    else:
        single_rooms = 12
        duplication_factor = 1
    num_rooms = single_rooms * duplication_factor
    client.select(problem_name)

    plan_count = 1
    plans = [''.join(random.choices("012345", k=num_rooms * 6)) for _ in range(plan_count)]

    results_ints = client.explore(plans)["results"]
    results = [''.join(map(str, result_ints)) for result_ints in results_ints]

    print(f"plan: {plans}")
    print(f"result: {results}")

    estimated_aedificium = solve(num_rooms, plans, results)
    if estimated_aedificium is None:
        print("z3が解を見つけられませんでした")
        return

    # print(f"estimated_aedificium: {estimated_aedificium.to_dict()}")
    guess_response = client.guess(estimated_aedificium.to_dict())
    print(f"guess_response: {guess_response}")



if __name__ == "__main__":
    main()

