"""Position taxonomy for the fight engine."""

DISTANCE = "distance"
CLINCH = "clinch"
GUARD = "guard"
HALF_GUARD = "half_guard"
SIDE_CONTROL = "side_control"
MOUNT = "mount"
BACK_CONTROL = "back_control"

GROUND_POSITIONS = (GUARD, HALF_GUARD, SIDE_CONTROL, MOUNT, BACK_CONTROL)

# Ground position value from the top player's perspective, used to bias
# "advance" vs. "retreat" transitions and to weight round-scoring effectiveness.
POSITION_DOMINANCE = {
    GUARD: 1,
    HALF_GUARD: 2,
    SIDE_CONTROL: 3,
    MOUNT: 4,
    BACK_CONTROL: 4,
}

# Ordered chain a top player advances through when passing guard.
ADVANCE_CHAIN = [GUARD, HALF_GUARD, SIDE_CONTROL, MOUNT]

POSITION_LABELS = {
    DISTANCE: "at distance",
    CLINCH: "in the clinch",
    GUARD: "in guard",
    HALF_GUARD: "in half guard",
    SIDE_CONTROL: "in side control",
    MOUNT: "in mount",
    BACK_CONTROL: "with back control",
}

# bare noun phrases, for templates that already supply their own preposition
# ("works to {name}", "landing in {name}")
POSITION_NAMES = {
    DISTANCE: "distance",
    CLINCH: "the clinch",
    GUARD: "guard",
    HALF_GUARD: "half guard",
    SIDE_CONTROL: "side control",
    MOUNT: "mount",
    BACK_CONTROL: "back control",
}


def other(key: str) -> str:
    return "B" if key == "A" else "A"
