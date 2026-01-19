#!/usr/bin/env python3
"""Convert .ectt files to .ctt format.

Conversion rules:
- Header: UnavailabilityConstraints -> Constraints
- Header: Remove Min_Max_Daily_Lectures and RoomConstraints lines
- COURSES: Remove 6th field (DoubleLectures)
- ROOMS: Remove 3rd field (Building)
- Remove ROOM_CONSTRAINTS section entirely
"""

import sys
from pathlib import Path


def convert_ectt_to_ctt(ectt_path: Path) -> str:
    """Convert an .ectt file to .ctt format."""
    lines = ectt_path.read_text().splitlines()
    result = []
    section = "header"
    skip_section = False

    for line in lines:
        stripped = line.strip()

        # Detect section changes
        if stripped == "COURSES:":
            section = "courses"
            skip_section = False
            result.append(line)
            continue
        elif stripped == "ROOMS:":
            section = "rooms"
            skip_section = False
            result.append(line)
            continue
        elif stripped == "CURRICULA:":
            section = "curricula"
            skip_section = False
            result.append(line)
            continue
        elif stripped == "UNAVAILABILITY_CONSTRAINTS:":
            section = "unavailability"
            skip_section = False
            result.append(line)
            continue
        elif stripped == "ROOM_CONSTRAINTS:":
            section = "room_constraints"
            skip_section = True
            continue
        elif stripped == "END.":
            section = "end"
            skip_section = False
            result.append(line)
            continue

        # Skip ROOM_CONSTRAINTS section
        if skip_section:
            continue

        # Process based on section
        if section == "header":
            if stripped.startswith("UnavailabilityConstraints:"):
                # Convert to Constraints
                num = stripped.split(":")[1].strip()
                result.append(f"Constraints: {num}")
            elif stripped.startswith("Min_Max_Daily_Lectures:"):
                # Skip this line
                continue
            elif stripped.startswith("RoomConstraints:"):
                # Skip this line
                continue
            else:
                result.append(line)
        elif section == "courses":
            if stripped:
                # Remove 6th field
                parts = stripped.split()
                if len(parts) >= 6:
                    result.append(" ".join(parts[:5]))
                else:
                    result.append(line)
            else:
                result.append(line)
        elif section == "rooms":
            if stripped:
                # Remove 3rd field
                parts = stripped.split()
                if len(parts) >= 3:
                    result.append(" ".join(parts[:2]))
                else:
                    result.append(line)
            else:
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result) + "\n"


def main():
    benchmark_dir = Path(__file__).parent / "benchmark"
    ectt_files = sorted(benchmark_dir.glob("*.ectt"))

    print(f"Found {len(ectt_files)} .ectt files")

    for ectt_path in ectt_files:
        ctt_path = ectt_path.with_suffix(".ctt")
        print(f"Converting: {ectt_path.name} -> {ctt_path.name}")

        ctt_content = convert_ectt_to_ctt(ectt_path)
        ctt_path.write_text(ctt_content)

    print(f"\nDone. Converted {len(ectt_files)} files.")


if __name__ == "__main__":
    main()
