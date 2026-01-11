#!/usr/bin/env python3
"""
Curriculum-Based Course Timetabling (CB-CTT) Validator and Visualizer.

Usage:
    python validator.py <input_file> <solution_file> [--no-visual]

Example:
    python validator.py examples/toy.ctt examples/toy_solved.out
"""

import sys
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Course:
    name: str
    teacher: str
    num_lectures: int
    min_working_days: int
    num_students: int


@dataclass
class Room:
    name: str
    capacity: int


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

    @property
    def num_periods(self) -> int:
        return self.num_days * self.periods_per_day

    def course_by_name(self, name: str) -> Course | None:
        for c in self.courses:
            if c.name == name:
                return c
        return None

    def room_by_name(self, name: str) -> Room | None:
        for r in self.rooms:
            if r.name == name:
                return r
        return None

    def curricula_for_course(self, course_name: str) -> list[Curriculum]:
        return [cur for cur in self.curricula if course_name in cur.course_names]


@dataclass
class Assignment:
    course_name: str
    room_name: str
    day: int
    period: int


def parse_instance(filename: str) -> Instance:
    """Parse a .ctt input file."""
    instance = Instance(name="")

    with open(filename, "r") as f:
        lines = f.readlines()

    i = 0
    num_courses = 0
    num_rooms = 0
    num_curricula = 0
    num_constraints = 0

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
            num_constraints = int(line.split(":")[1].strip())
        elif line == "COURSES:":
            break

    # Parse courses
    for _ in range(num_courses):
        line = lines[i].strip()
        i += 1
        parts = line.split()
        instance.courses.append(
            Course(
                name=parts[0],
                teacher=parts[1],
                num_lectures=int(parts[2]),
                min_working_days=int(parts[3]),
                num_students=int(parts[4]),
            )
        )

    # Skip to ROOMS:
    while i < len(lines) and lines[i].strip() != "ROOMS:":
        i += 1
    i += 1

    # Parse rooms
    for _ in range(num_rooms):
        line = lines[i].strip()
        i += 1
        parts = line.split()
        instance.rooms.append(Room(name=parts[0], capacity=int(parts[1])))

    # Skip to CURRICULA:
    while i < len(lines) and lines[i].strip() != "CURRICULA:":
        i += 1
    i += 1

    # Parse curricula
    for _ in range(num_curricula):
        line = lines[i].strip()
        i += 1
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
    for _ in range(num_constraints):
        if i >= len(lines):
            break
        line = lines[i].strip()
        i += 1
        if line == "END." or not line:
            break
        parts = line.split()
        course_name = parts[0]
        day = int(parts[1])
        period = int(parts[2])
        instance.unavailable.add((course_name, day, period))

    return instance


def parse_solution(filename: str) -> list[Assignment]:
    """Parse a solution file."""
    assignments = []
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 4:
                assignments.append(
                    Assignment(
                        course_name=parts[0],
                        room_name=parts[1],
                        day=int(parts[2]),
                        period=int(parts[3]),
                    )
                )
    return assignments


# Penalty weights
MIN_WORKING_DAYS_PENALTY = 5
CURRICULUM_COMPACTNESS_PENALTY = 2
ROOM_STABILITY_PENALTY = 1


@dataclass
class ValidationResult:
    # Hard constraint violations
    lectures_violations: list[str] = field(default_factory=list)
    conflict_violations: list[str] = field(default_factory=list)
    availability_violations: list[str] = field(default_factory=list)
    room_occupation_violations: list[str] = field(default_factory=list)

    # Soft constraint violations
    room_capacity_violations: list[str] = field(default_factory=list)
    min_working_days_violations: list[str] = field(default_factory=list)
    curriculum_compactness_violations: list[str] = field(default_factory=list)
    room_stability_violations: list[str] = field(default_factory=list)

    # Costs
    room_capacity_cost: int = 0
    min_working_days_cost: int = 0
    curriculum_compactness_cost: int = 0
    room_stability_cost: int = 0

    @property
    def hard_violations(self) -> int:
        return (
            len(self.lectures_violations)
            + len(self.conflict_violations)
            + len(self.availability_violations)
            + len(self.room_occupation_violations)
        )

    @property
    def total_cost(self) -> int:
        return (
            self.room_capacity_cost
            + self.min_working_days_cost
            + self.curriculum_compactness_cost
            + self.room_stability_cost
        )


def validate(instance: Instance, assignments: list[Assignment]) -> ValidationResult:
    """Validate a solution against the instance."""
    result = ValidationResult()

    # Build lookup structures
    # course -> list of (room, day, period)
    course_assignments: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    # (day, period) -> list of (course, room)
    period_assignments: dict[tuple[int, int], list[tuple[str, str]]] = defaultdict(list)
    # (room, day, period) -> list of courses
    room_period_assignments: dict[tuple[str, int, int], list[str]] = defaultdict(list)

    for a in assignments:
        course_assignments[a.course_name].append((a.room_name, a.day, a.period))
        period_assignments[(a.day, a.period)].append((a.course_name, a.room_name))
        room_period_assignments[(a.room_name, a.day, a.period)].append(a.course_name)

    # ========== HARD CONSTRAINTS ==========

    # H1: Lectures - each course must have exactly the required number of lectures
    for course in instance.courses:
        actual = len(course_assignments[course.name])
        if actual < course.num_lectures:
            result.lectures_violations.append(
                f"[H] Too few lectures for course {course.name}"
            )
        elif actual > course.num_lectures:
            result.lectures_violations.append(
                f"[H] Too many lectures for course {course.name}"
            )

    # H3 & H4: Conflicts - teacher conflicts and curriculum conflicts
    # Build conflict pairs
    conflict_pairs: set[tuple[str, str]] = set()

    # Teacher conflicts
    teacher_courses: dict[str, list[str]] = defaultdict(list)
    for course in instance.courses:
        teacher_courses[course.teacher].append(course.name)
    for teacher, courses in teacher_courses.items():
        for i, c1 in enumerate(courses):
            for c2 in courses[i + 1 :]:
                conflict_pairs.add((min(c1, c2), max(c1, c2)))

    # Curriculum conflicts
    for curriculum in instance.curricula:
        courses = curriculum.course_names
        for i, c1 in enumerate(courses):
            for c2 in courses[i + 1 :]:
                conflict_pairs.add((min(c1, c2), max(c1, c2)))

    # Check conflicts
    for (day, period), courses_rooms in period_assignments.items():
        courses_at_period = [cr[0] for cr in courses_rooms]
        for i, c1 in enumerate(courses_at_period):
            for c2 in courses_at_period[i + 1 :]:
                pair = (min(c1, c2), max(c1, c2))
                if pair in conflict_pairs:
                    p = day * instance.periods_per_day + period
                    result.conflict_violations.append(
                        f"[H] Courses {c1} and {c2} have both a lecture at period {p} "
                        f"(day {day}, timeslot {period})"
                    )

    # H5: Availability - courses can't be scheduled at unavailable periods
    for a in assignments:
        if (a.course_name, a.day, a.period) in instance.unavailable:
            p = a.day * instance.periods_per_day + a.period
            result.availability_violations.append(
                f"[H] Course {a.course_name} has a lecture at unavailable period {p} "
                f"(day {a.day}, timeslot {a.period})"
            )

    # H2: Room occupation - at most one lecture per room per period
    for (room, day, period), courses in room_period_assignments.items():
        if len(courses) > 1:
            p = day * instance.periods_per_day + period
            msg = (
                f"[H] {len(courses)} lectures in room {room} the period {p} "
                f"(day {day}, timeslot {period})"
            )
            if len(courses) > 2:
                msg += f" [{len(courses) - 1} violations]"
            result.room_occupation_violations.append(msg)

    # ========== SOFT CONSTRAINTS ==========

    # S1: Room capacity
    for a in assignments:
        course = instance.course_by_name(a.course_name)
        room = instance.room_by_name(a.room_name)
        if course and room and course.num_students > room.capacity:
            penalty = course.num_students - room.capacity
            result.room_capacity_cost += penalty
            p = a.day * instance.periods_per_day + a.period
            result.room_capacity_violations.append(
                f"[S({penalty})] Room {room.name} too small for course {course.name} "
                f"the period {p} (day {a.day}, timeslot {a.period})"
            )

    # S2: Minimum working days
    for course in instance.courses:
        days_used = set()
        for room, day, period in course_assignments[course.name]:
            days_used.add(day)
        if len(days_used) < course.min_working_days:
            missing = course.min_working_days - len(days_used)
            result.min_working_days_cost += missing * MIN_WORKING_DAYS_PENALTY
            result.min_working_days_violations.append(
                f"[S({MIN_WORKING_DAYS_PENALTY})] The course {course.name} has only "
                f"{len(days_used)} days of lecture"
            )

    # S3: Curriculum compactness
    for curriculum in instance.curricula:
        for day in range(instance.num_days):
            for period in range(instance.periods_per_day):
                # Check if curriculum has a lecture at this period
                has_lecture = False
                for course_name in curriculum.course_names:
                    for room, d, p in course_assignments[course_name]:
                        if d == day and p == period:
                            has_lecture = True
                            break
                    if has_lecture:
                        break

                if not has_lecture:
                    continue

                # Check adjacent periods (same day)
                has_adjacent = False
                for adj_period in [period - 1, period + 1]:
                    if adj_period < 0 or adj_period >= instance.periods_per_day:
                        continue
                    for course_name in curriculum.course_names:
                        for room, d, p in course_assignments[course_name]:
                            if d == day and p == adj_period:
                                has_adjacent = True
                                break
                        if has_adjacent:
                            break
                    if has_adjacent:
                        break

                if not has_adjacent:
                    result.curriculum_compactness_cost += CURRICULUM_COMPACTNESS_PENALTY
                    p_idx = day * instance.periods_per_day + period
                    result.curriculum_compactness_violations.append(
                        f"[S({CURRICULUM_COMPACTNESS_PENALTY})] Curriculum {curriculum.name} "
                        f"has an isolated lecture at period {p_idx} (day {day}, timeslot {period})"
                    )

    # S4: Room stability
    for course in instance.courses:
        rooms_used = set()
        for room, day, period in course_assignments[course.name]:
            rooms_used.add(room)
        if len(rooms_used) > 1:
            extra = len(rooms_used) - 1
            result.room_stability_cost += extra * ROOM_STABILITY_PENALTY
            result.room_stability_violations.append(
                f"[S({extra * ROOM_STABILITY_PENALTY})] Course {course.name} uses "
                f"{len(rooms_used)} different rooms"
            )

    return result


def print_validation_result(result: ValidationResult):
    """Print validation results in the same format as the C++ validator."""
    # Print all violations
    for v in result.lectures_violations:
        print(v)
    for v in result.conflict_violations:
        print(v)
    for v in result.availability_violations:
        print(v)
    for v in result.room_occupation_violations:
        print(v)
    for v in result.room_capacity_violations:
        print(v)
    for v in result.min_working_days_violations:
        print(v)
    for v in result.curriculum_compactness_violations:
        print(v)
    for v in result.room_stability_violations:
        print(v)

    print()
    print(f"Violations of Lectures (hard) : {len(result.lectures_violations)}")
    print(f"Violations of Conflicts (hard) : {len(result.conflict_violations)}")
    print(f"Violations of Availability (hard) : {len(result.availability_violations)}")
    print(f"Violations of RoomOccupation (hard) : {len(result.room_occupation_violations)}")
    print(f"Cost of RoomCapacity (soft) : {result.room_capacity_cost}")
    print(f"Cost of MinWorkingDays (soft) : {result.min_working_days_cost}")
    print(f"Cost of CurriculumCompactness (soft) : {result.curriculum_compactness_cost}")
    print(f"Cost of RoomStability (soft) : {result.room_stability_cost}")

    print()
    if result.hard_violations > 0:
        print(f"Summary: Violations = {result.hard_violations}, Total Cost = {result.total_cost}")
    else:
        print(f"Summary: Total Cost = {result.total_cost}")


def visualize_timetable(instance: Instance, assignments: list[Assignment]):
    """Visualize the timetable."""
    # Build lookup: (room, day, period) -> course
    room_schedule: dict[str, dict[tuple[int, int], str]] = {
        room.name: {} for room in instance.rooms
    }
    for a in assignments:
        key = (a.day, a.period)
        if key in room_schedule.get(a.room_name, {}):
            # Multiple courses in same slot - append
            room_schedule[a.room_name][key] += f", {a.course_name}"
        else:
            if a.room_name in room_schedule:
                room_schedule[a.room_name][key] = a.course_name

    # Day names
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Calculate column width
    max_course_len = max((len(c.name) for c in instance.courses), default=5)
    col_width = max(max_course_len + 2, 8)

    def format_cell(content: str, width: int) -> str:
        if len(content) > width:
            return content[: width - 1] + "…"
        return content.center(width)

    print("\n" + "=" * 60)
    print("TIMETABLE VISUALIZATION")
    print("=" * 60)

    # Print room-based timetables
    for room in instance.rooms:
        print(f"\n【Room {room.name}】(Capacity: {room.capacity})")
        print("-" * (8 + col_width * instance.num_days))

        # Header row
        header = "        "
        for d in range(instance.num_days):
            day_label = day_names[d] if d < len(day_names) else f"Day{d}"
            header += format_cell(f"{day_label}({d})", col_width)
        print(header)

        # Period rows
        for p in range(instance.periods_per_day):
            row = f"P{p}({p})  "
            for d in range(instance.num_days):
                course = room_schedule[room.name].get((d, p), "-")
                row += format_cell(course, col_width)
            print(row)

    # Print curriculum-based timetables
    for curriculum in instance.curricula:
        print(f"\n【Curriculum {curriculum.name}】({', '.join(curriculum.course_names)})")
        print("-" * (8 + col_width * instance.num_days))

        # Build curriculum schedule
        cur_schedule: dict[tuple[int, int], list[str]] = defaultdict(list)
        for a in assignments:
            if a.course_name in curriculum.course_names:
                cur_schedule[(a.day, a.period)].append(a.course_name)

        # Header row
        header = "        "
        for d in range(instance.num_days):
            day_label = day_names[d] if d < len(day_names) else f"Day{d}"
            header += format_cell(f"{day_label}({d})", col_width)
        print(header)

        # Period rows
        for p in range(instance.periods_per_day):
            row = f"P{p}({p})  "
            for d in range(instance.num_days):
                courses = cur_schedule.get((d, p), [])
                if not courses:
                    cell = "-"
                elif len(courses) == 1:
                    cell = courses[0]
                else:
                    # Conflict!
                    cell = "!" + ",".join(courses)
                row += format_cell(cell, col_width)
            print(row)

    # Print course summary
    print("\n" + "=" * 60)
    print("COURSE SUMMARY")
    print("=" * 60)
    print(f"{'Course':<12} {'Teacher':<12} {'Lec':<4} {'Days':<5} {'Students':<8} {'Rooms'}")
    print("-" * 60)

    course_assignments: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for a in assignments:
        course_assignments[a.course_name].append((a.room_name, a.day, a.period))

    for course in instance.courses:
        assigns = course_assignments[course.name]
        days_used = sorted(set(a[1] for a in assigns))
        rooms_used = sorted(set(a[0] for a in assigns))
        days_str = ",".join(str(d) for d in days_used)
        rooms_str = ",".join(rooms_used)
        print(
            f"{course.name:<12} {course.teacher:<12} "
            f"{len(assigns)}/{course.num_lectures:<2} "
            f"{len(days_used)}/{course.min_working_days:<2}  "
            f"{course.num_students:<8} {rooms_str}"
        )


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_file> <solution_file> [--no-visual]")
        sys.exit(1)

    input_file = sys.argv[1]
    solution_file = sys.argv[2]
    show_visual = "--no-visual" not in sys.argv

    # Parse files
    instance = parse_instance(input_file)
    assignments = parse_solution(solution_file)

    # Validate
    result = validate(instance, assignments)
    print_validation_result(result)

    # Visualize
    if show_visual:
        visualize_timetable(instance, assignments)


if __name__ == "__main__":
    main()
