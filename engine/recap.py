"""Plain-text event recaps, formatted to be pasted/shared anywhere."""

import sqlite3

from models import event as event_model


def export_event_text(conn: sqlite3.Connection, event_id: int) -> str:
    event = event_model.get_event(conn, event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found")
    bouts = event_model.list_bouts(conn, event_id)

    lines = ["=" * 60, event["name"].upper()]
    lines.append(event["event_date"] + (f" -- {event['venue']}" if event["venue"] else ""))
    lines.append("=" * 60)
    lines.append("")

    for segment, label in (("main", "MAIN CARD"), ("prelim", "PRELIMS")):
        segment_bouts = sorted((b for b in bouts if b["card_segment"] == segment), key=lambda b: b["bout_order"])
        if not segment_bouts:
            continue
        lines.append(label)
        lines.append("-" * len(label))
        for b in segment_bouts:
            tags = []
            if b["is_title_fight"]:
                tags.append("INTERIM TITLE FIGHT" if b["is_interim_title_fight"] else "TITLE FIGHT")
            if b["is_number_one_contender"]:
                tags.append("#1 CONTENDER FIGHT")
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            lines.append(f"{b['weight_class']}{tag_str}")

            if b["status"] != "Completed":
                lines.append(f"{b['fighter_a_name']} vs. {b['fighter_b_name']} (not yet contested)")
            elif b["winner_id"] is None:
                lines.append(f"{b['fighter_a_name']} vs. {b['fighter_b_name']} -- Draw ({b['method_detail']})")
            else:
                is_a_winner = b["winner_id"] == b["fighter_a_id"]
                winner = b["fighter_a_name"] if is_a_winner else b["fighter_b_name"]
                loser = b["fighter_b_name"] if is_a_winner else b["fighter_a_name"]
                lines.append(f"{winner} def. {loser}")
                lines.append(f"  via {b['method_detail']}, Round {b['result_round']}, {b['result_time']}")
            lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
