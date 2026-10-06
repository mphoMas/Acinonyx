#!/usr/bin/env python3
"""
about_me/comms_tracker.py: Developer CLI to inspect personal communication vault,
linguistic patterns, understanding milestones, and engagement stats.

Usage:
    python3 about_me/comms_tracker.py sync
    python3 about_me/comms_tracker.py profile
    python3 about_me/comms_tracker.py activity
    python3 about_me/comms_tracker.py search "search query"
    python3 about_me/comms_tracker.py query "SELECT * FROM v_top_vocabulary LIMIT 10;"
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mas.memory.comms_vault import CommsVault, DEFAULT_DB_PATH


def print_table(headers: list, rows: list):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(sep_line)
    for row in rows:
        print(" | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)))


def main():
    vault = CommsVault(DEFAULT_DB_PATH)
    args = sys.argv[1:]
    command = args[0] if args else "profile"

    if command == "sync":
        print(f"[*] Syncing transcripts from Antigravity brain...")
        res = vault.sync_brain_transcripts()
        print(f"[✓] Synced: {res['conversations_scanned']} conversations, {res['messages_ingested']} messages updated.")

    elif command == "profile":
        profile = vault.get_user_profile_summary()
        metrics = profile["communication_metrics"]
        print("\n" + "=" * 60)
        print("👤 MPHO MASHILE — COGNITIVE & LINGUISTIC VAULT PROFILE")
        print("=" * 60)
        print(f"• Total User Turns:        {metrics.get('total_turns', 0)}")
        print(f"• Total Words Communicated: {metrics.get('total_words', 0)}")
        print(f"• Avg Words per Prompt:     {metrics.get('avg_words_per_turn', 0):.1f}")
        print("\n--- 🗣️ Top Vocabulary Terms ---")
        vocab_rows = [[v['term'], v['category'], v['frequency']] for v in profile['frequent_vocabulary'][:15]]
        print_table(["Term", "Category", "Frequency"], vocab_rows)

        print("\n--- 🧠 Key Concepts & Understanding Depth ---")
        milestones = [[m['concept'], m['depth_level'], m['count']] for m in profile['comprehension_trajectory'][:10]]
        print_table(["Concept", "Depth Level", "Touchpoints"], milestones)
        print("=" * 60 + "\n")

    elif command == "activity":
        with vault.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM v_daily_activity;")
            rows = cursor.fetchall()
            print("\n📅 Daily Engagement Cadence:")
            print_table(["Date", "User Turns", "Agent Turns", "Words Written"], [list(r) for r in rows])
            print()

    elif command == "search":
        if len(args) < 2:
            print("Usage: python3 about_me/comms_tracker.py search <term>")
            return
        query = args[1]
        matches = vault.search_comms(query, limit=5)
        print(f"\n🔍 Search Results for '{query}' ({len(matches)} found):")
        for m in matches:
            print(f"[{m['timestamp']}] ({m['sender']}): {m['clean_content'][:180]}...")
            print("-" * 50)
        print()

    elif command == "query":
        if len(args) < 2:
            print("Usage: python3 about_me/comms_tracker.py query \"SELECT ...\"")
            return
        sql = args[1]
        with vault.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            if rows:
                headers = list(rows[0].keys())
                print_table(headers, [list(r) for r in rows])
            else:
                print("(0 rows returned)")

    else:
        print("Unknown command. Options: sync, profile, activity, search, query")


if __name__ == "__main__":
    main()
