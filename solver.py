#!/usr/bin/env python3
"""
Curriculum-Based Course Timetabling (CB-CTT) Solver using OR-Tools CP-SAT.

Usage:
    python solver.py <input_file> [output_file]

Example:
    python solver.py examples/toy.ctt examples/toy_solution.out
"""

import sys
from dataclasses import dataclass, field
from ortools.sat.python import cp_model


@dataclass
class Course:
    name: str
    teacher: str
    num_lectures: int
    min_working_days: int
    num_students: int
    double_lectures: int = 0  # ectt: 1 if double lectures required


@dataclass
class Room:
    name: str
    capacity: int
    site: int = 0  # ectt: building/site identifier


@dataclass
class Curriculum:
    name: str
    course_names: list[str] = field(default_factory=list)


@dataclass
class Instance:
    name: str
    courses: list[Course] = field(default_factory=list)
    rooms: list[Room] = field(default_factory=list)
    curricula: list[Curriculum] = field(default_factory=list)
    num_days: int = 0
    periods_per_day: int = 0
    unavailable: set[tuple[str, int, int]] = field(default_factory=set)
    # ectt extensions
    min_daily_lectures: int = 0
    max_daily_lectures: int = 0
    room_constraints: dict[str, set[str]] = field(default_factory=dict)  # course -> allowed rooms

    @property
    def num_periods(self) -> int:
        return self.num_days * self.periods_per_day

    def course_index(self, name: str) -> int:
        for i, c in enumerate(self.courses):
            if c.name == name:
                return i
        return -1

    def room_index(self, name: str) -> int:
        for i, r in enumerate(self.rooms):
            if r.name == name:
                return i
        return -1


def parse_instance(filename: str) -> Instance:
    """Parse a .ctt or .ectt input file."""
    instance = Instance(name="")

    with open(filename, "r") as f:
        lines = f.readlines()

    i = 0
    num_courses = 0
    num_rooms = 0
    num_curricula = 0
    num_unavail_constraints = 0
    num_room_constraints = 0
    is_ectt = False

    # Parse header
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line.startswith("Name:"):
            instance.name = line.split(":")[1].strip()
        elif line.startswith("Courses:"):
            num_courses = int(line.split(":")[1].strip())
        elif line.startswith("Rooms:"):
            num_rooms = int(line.split(":")[1].strip())
        elif line.startswith("Days:"):
            instance.num_days = int(line.split(":")[1].strip())
        elif line.startswith("Periods_per_day:"):
            instance.periods_per_day = int(line.split(":")[1].strip())
        elif line.startswith("Curricula:"):
            num_curricula = int(line.split(":")[1].strip())
        elif line.startswith("Constraints:"):
            # ctt format
            num_unavail_constraints = int(line.split(":")[1].strip())
        elif line.startswith("Min_Max_Daily_Lectures:"):
            # ectt format
            is_ectt = True
            parts = line.split(":")[1].strip().split()
            instance.min_daily_lectures = int(parts[0])
            instance.max_daily_lectures = int(parts[1])
        elif line.startswith("UnavailabilityConstraints:"):
            # ectt format
            is_ectt = True
            num_unavail_constraints = int(line.split(":")[1].strip())
        elif line.startswith("RoomConstraints:"):
            # ectt format
            num_room_constraints = int(line.split(":")[1].strip())
        elif line == "COURSES:":
            break

    # Parse courses
    for _ in range(num_courses):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        parts = line.split()
        course = Course(
            name=parts[0],
            teacher=parts[1],
            num_lectures=int(parts[2]),
            min_working_days=int(parts[3]),
            num_students=int(parts[4]),
        )
        # ectt format has 6th field: double_lectures
        if len(parts) >= 6:
            course.double_lectures = int(parts[5])
        instance.courses.append(course)

    # Skip to ROOMS:
    while i < len(lines) and lines[i].strip() != "ROOMS:":
        i += 1
    i += 1

    # Parse rooms
    for _ in range(num_rooms):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        parts = line.split()
        room = Room(name=parts[0], capacity=int(parts[1]))
        # ectt format has 3rd field: site
        if len(parts) >= 3:
            room.site = int(parts[2])
        instance.rooms.append(room)

    # Skip to CURRICULA:
    while i < len(lines) and lines[i].strip() != "CURRICULA:":
        i += 1
    i += 1

    # Parse curricula
    for _ in range(num_curricula):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        parts = line.split()
        curriculum = Curriculum(name=parts[0])
        num_members = int(parts[1])
        curriculum.course_names = parts[2 : 2 + num_members]
        instance.curricula.append(curriculum)

    # Skip to UNAVAILABILITY_CONSTRAINTS:
    while i < len(lines) and lines[i].strip() != "UNAVAILABILITY_CONSTRAINTS:":
        i += 1
    i += 1

    # Parse unavailability constraints
    count = 0
    while i < len(lines) and count < num_unavail_constraints:
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line.startswith("ROOM_CONSTRAINTS:") or line == "END.":
            break
        parts = line.split()
        if len(parts) >= 3:
            course_name = parts[0]
            day = int(parts[1])
            period = int(parts[2])
            instance.unavailable.add((course_name, day, period))
            count += 1

    # Parse room constraints (ectt format)
    if num_room_constraints > 0:
        # Skip to ROOM_CONSTRAINTS:
        while i < len(lines) and lines[i].strip() != "ROOM_CONSTRAINTS:":
            i += 1
        i += 1

        count = 0
        while i < len(lines) and count < num_room_constraints:
            line = lines[i].strip()
            i += 1
            if not line:
                continue
            if line == "END.":
                break
            parts = line.split()
            if len(parts) >= 2:
                course_name = parts[0]
                room_name = parts[1]
                if course_name not in instance.room_constraints:
                    instance.room_constraints[course_name] = set()
                instance.room_constraints[course_name].add(room_name)
                count += 1

    return instance


# Penalty weights
ROOM_CAPACITY_PENALTY = 1
MIN_WORKING_DAYS_PENALTY = 5
CURRICULUM_COMPACTNESS_PENALTY = 2
ROOM_STABILITY_PENALTY = 1


def solve(instance: Instance, time_limit: float = 60.0) -> dict | None:
    """
    Solve the CB-CTT problem using CP-SAT.

    Returns a dictionary mapping (course_index, lecture_index) -> (room_index, day, period)
    or None if no solution found.
    """
    model = cp_model.CpModel()

    num_courses = len(instance.courses)
    num_rooms = len(instance.rooms)
    num_days = instance.num_days
    periods_per_day = instance.periods_per_day
    num_periods = instance.num_periods

    # Decision variables: x[c][l][r][p] = 1 if lecture l of course c is in room r at period p
    # We use a flattened representation for efficiency
    # For each course c and lecture l, we have variables for room and period

    # x[c, l, r, p] = 1 if lecture l of course c is assigned to room r at period p
    x = {}
    for c, course in enumerate(instance.courses):
        # Get allowed rooms for this course (if room constraints exist)
        allowed_rooms = instance.room_constraints.get(course.name)

        for l in range(course.num_lectures):
            for r, room in enumerate(instance.rooms):
                # H6: Room constraints - course can only use allowed rooms
                if allowed_rooms is not None and room.name not in allowed_rooms:
                    continue

                for p in range(num_periods):
                    day = p // periods_per_day
                    period_in_day = p % periods_per_day
                    # H5: Check unavailability
                    if (course.name, day, period_in_day) in instance.unavailable:
                        continue
                    x[c, l, r, p] = model.NewBoolVar(f"x_c{c}_l{l}_r{r}_p{p}")

    # ========== HARD CONSTRAINTS ==========

    # H1: Each lecture must be assigned to exactly one (room, period)
    for c, course in enumerate(instance.courses):
        for l in range(course.num_lectures):
            valid_assignments = [
                x[c, l, r, p]
                for r in range(num_rooms)
                for p in range(num_periods)
                if (c, l, r, p) in x
            ]
            model.AddExactlyOne(valid_assignments)

    # H2: Room occupancy - at most one lecture per room per period
    for r in range(num_rooms):
        for p in range(num_periods):
            lectures_in_room = [
                x[c, l, r, p]
                for c, course in enumerate(instance.courses)
                for l in range(course.num_lectures)
                if (c, l, r, p) in x
            ]
            model.AddAtMostOne(lectures_in_room)

    # H3: Teacher conflicts - a teacher can only teach one lecture per period
    teacher_courses: dict[str, list[int]] = {}
    for c, course in enumerate(instance.courses):
        if course.teacher not in teacher_courses:
            teacher_courses[course.teacher] = []
        teacher_courses[course.teacher].append(c)

    for teacher, courses_idx in teacher_courses.items():
        if len(courses_idx) <= 1:
            continue
        for p in range(num_periods):
            lectures_at_period = [
                x[c, l, r, p]
                for c in courses_idx
                for l in range(instance.courses[c].num_lectures)
                for r in range(num_rooms)
                if (c, l, r, p) in x
            ]
            model.AddAtMostOne(lectures_at_period)

    # H4: Curriculum conflicts - courses in same curriculum can't be at same period
    for curriculum in instance.curricula:
        course_indices = [
            instance.course_index(name) for name in curriculum.course_names
        ]
        course_indices = [c for c in course_indices if c >= 0]
        if len(course_indices) <= 1:
            continue
        for p in range(num_periods):
            lectures_at_period = [
                x[c, l, r, p]
                for c in course_indices
                for l in range(instance.courses[c].num_lectures)
                for r in range(num_rooms)
                if (c, l, r, p) in x
            ]
            model.AddAtMostOne(lectures_at_period)

    # H5: Unavailability is already handled by not creating variables
    # H6: Room constraints (ectt) are handled by not creating variables

    # ========== SOFT CONSTRAINTS ==========

    soft_costs = []

    # S1: Room capacity - penalty for each student over capacity
    for c, course in enumerate(instance.courses):
        for l in range(course.num_lectures):
            for r, room in enumerate(instance.rooms):
                if course.num_students > room.capacity:
                    penalty = course.num_students - room.capacity
                    for p in range(num_periods):
                        if (c, l, r, p) in x:
                            soft_costs.append(x[c, l, r, p] * penalty)

    # S2: Minimum working days
    # For each course, count distinct days used
    for c, course in enumerate(instance.courses):
        # day_used[d] = 1 if course c has at least one lecture on day d
        day_used = {}
        for d in range(num_days):
            day_used[d] = model.NewBoolVar(f"day_used_c{c}_d{d}")
            lectures_on_day = [
                x[c, l, r, p]
                for l in range(course.num_lectures)
                for r in range(num_rooms)
                for p in range(d * periods_per_day, (d + 1) * periods_per_day)
                if (c, l, r, p) in x
            ]
            if lectures_on_day:
                model.AddMaxEquality(day_used[d], lectures_on_day)
            else:
                model.Add(day_used[d] == 0)

        # Count working days
        working_days = model.NewIntVar(0, num_days, f"working_days_c{c}")
        model.Add(working_days == sum(day_used.values()))

        # Penalty for missing days
        if course.min_working_days > 0:
            missing_days = model.NewIntVar(
                0, course.min_working_days, f"missing_days_c{c}"
            )
            model.Add(missing_days >= course.min_working_days - working_days)
            model.Add(missing_days >= 0)
            soft_costs.append(missing_days * MIN_WORKING_DAYS_PENALTY)

    # S3: Curriculum compactness - penalty for isolated lectures
    for g, curriculum in enumerate(instance.curricula):
        course_indices = [
            instance.course_index(name) for name in curriculum.course_names
        ]
        course_indices = [c for c in course_indices if c >= 0]

        for d in range(num_days):
            for t in range(periods_per_day):
                p = d * periods_per_day + t

                # has_lecture[p] = 1 if curriculum has a lecture at period p
                lectures_at_p = [
                    x[c, l, r, p]
                    for c in course_indices
                    for l in range(instance.courses[c].num_lectures)
                    for r in range(num_rooms)
                    if (c, l, r, p) in x
                ]

                if not lectures_at_p:
                    continue

                has_lecture = model.NewBoolVar(f"has_lec_g{g}_p{p}")
                model.AddMaxEquality(has_lecture, lectures_at_p)

                # Check adjacent periods (same day only)
                has_adjacent = model.NewBoolVar(f"has_adj_g{g}_p{p}")

                adjacent_lectures = []
                if t > 0:  # Previous period
                    prev_p = p - 1
                    adjacent_lectures.extend(
                        [
                            x[c, l, r, prev_p]
                            for c in course_indices
                            for l in range(instance.courses[c].num_lectures)
                            for r in range(num_rooms)
                            if (c, l, r, prev_p) in x
                        ]
                    )
                if t < periods_per_day - 1:  # Next period
                    next_p = p + 1
                    adjacent_lectures.extend(
                        [
                            x[c, l, r, next_p]
                            for c in course_indices
                            for l in range(instance.courses[c].num_lectures)
                            for r in range(num_rooms)
                            if (c, l, r, next_p) in x
                        ]
                    )

                if adjacent_lectures:
                    model.AddMaxEquality(has_adjacent, adjacent_lectures)
                else:
                    model.Add(has_adjacent == 0)

                # Isolated if has_lecture and not has_adjacent
                is_isolated = model.NewBoolVar(f"isolated_g{g}_p{p}")
                model.Add(is_isolated >= has_lecture - has_adjacent)
                model.Add(is_isolated <= has_lecture)
                model.Add(is_isolated <= 1 - has_adjacent).OnlyEnforceIf(has_lecture)

                soft_costs.append(is_isolated * CURRICULUM_COMPACTNESS_PENALTY)

    # S4: Room stability - penalty for using multiple rooms
    for c, course in enumerate(instance.courses):
        if course.num_lectures <= 1:
            continue

        # room_used[r] = 1 if course c uses room r
        room_used = {}
        for r in range(num_rooms):
            room_used[r] = model.NewBoolVar(f"room_used_c{c}_r{r}")
            lectures_in_room = [
                x[c, l, r, p]
                for l in range(course.num_lectures)
                for p in range(num_periods)
                if (c, l, r, p) in x
            ]
            if lectures_in_room:
                model.AddMaxEquality(room_used[r], lectures_in_room)
            else:
                model.Add(room_used[r] == 0)

        # Count rooms used
        rooms_used = model.NewIntVar(0, num_rooms, f"rooms_used_c{c}")
        model.Add(rooms_used == sum(room_used.values()))

        # Penalty for extra rooms (rooms_used - 1, but at least 0)
        extra_rooms = model.NewIntVar(0, num_rooms, f"extra_rooms_c{c}")
        model.Add(extra_rooms >= rooms_used - 1)
        model.Add(extra_rooms >= 0)
        soft_costs.append(extra_rooms * ROOM_STABILITY_PENALTY)

    # Objective: minimize total soft cost
    total_cost = model.NewIntVar(0, 1000000, "total_cost")
    model.Add(total_cost == sum(soft_costs))
    model.Minimize(total_cost)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.log_search_progress = True

    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print(f"\nSolution found! Status: {solver.StatusName(status)}")
        print(f"Objective value (soft cost): {solver.ObjectiveValue()}")

        # Extract solution
        solution = {}
        for c, course in enumerate(instance.courses):
            for l in range(course.num_lectures):
                for r in range(num_rooms):
                    for p in range(num_periods):
                        if (c, l, r, p) in x and solver.Value(x[c, l, r, p]):
                            day = p // periods_per_day
                            period_in_day = p % periods_per_day
                            solution[c, l] = (r, day, period_in_day)
        return solution
    else:
        print(f"No solution found. Status: {solver.StatusName(status)}")
        return None


def write_solution(instance: Instance, solution: dict, filename: str):
    """Write solution to output file."""
    with open(filename, "w") as f:
        for c, course in enumerate(instance.courses):
            for l in range(course.num_lectures):
                if (c, l) in solution:
                    r, day, period = solution[c, l]
                    room_name = instance.rooms[r].name
                    f.write(f"{course.name} {room_name} {day} {period}\n")


def print_solution(instance: Instance, solution: dict):
    """Print solution to stdout."""
    print("\nSolution:")
    for c, course in enumerate(instance.courses):
        for l in range(course.num_lectures):
            if (c, l) in solution:
                r, day, period = solution[c, l]
                room_name = instance.rooms[r].name
                print(f"{course.name} {room_name} {day} {period}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_file> [output_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Parsing instance: {input_file}")
    instance = parse_instance(input_file)

    print(f"Instance: {instance.name}")
    print(f"  Courses: {len(instance.courses)}")
    print(f"  Rooms: {len(instance.rooms)}")
    print(f"  Days: {instance.num_days}")
    print(f"  Periods per day: {instance.periods_per_day}")
    print(f"  Curricula: {len(instance.curricula)}")
    print(f"  Unavailability constraints: {len(instance.unavailable)}")
    if instance.room_constraints:
        num_rc = sum(len(rooms) for rooms in instance.room_constraints.values())
        print(f"  Room constraints: {num_rc}")

    print("\nSolving...")
    solution = solve(instance)

    if solution:
        print_solution(instance, solution)
        if output_file:
            write_solution(instance, solution, output_file)
            print(f"\nSolution written to: {output_file}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
