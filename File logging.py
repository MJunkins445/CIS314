"""
Log analyzer:
1) Open the file
2) Read the file into a list
3) Filter out / remove log entries from "BotPoke"
4) Count the remaining log entries
5) Using a regular expression, list UNIQUE IP addresses from the remaining lines
"""
# Ran code using command: python C:\CIS314\log_analyzer.py C:\CIS314\access.log
from pathlib import Path
import re
import argparse
from typing import List

def read_lines(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()

def filter_out_botpoke(lines: List[str]) -> List[str]:
    return [ln for ln in lines if "BotPoke" not in ln]

  
def extract_unique_ips(lines: List[str]) -> List[str]: 
    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
    ips = (m.group(0) for ln in lines if (m := ip_re.search(ln)))
    # Sort numerically 
    unique_sorted = sorted(set(ips), key=lambda s: tuple(int(p) for p in s.split(".")))
    return unique_sorted


def main():
    parser = argparse.ArgumentParser(description="Analyze access log and extract unique IPs after removing 'BotPoke' entries.")
    parser.add_argument("-f", "--file", default=r"C:\CIS314\log", help="Path to access.log (default: C:\CIS314\log)")
    args = parser.parse_args()

    log_path = Path(args.file)
    if not log_path.exists():
        raise SystemExit(f"File not found: {log_path}")

    # 1. and 2. Open + read into list
    lines = read_lines(log_path)
    total_lines = len(lines)

    # 3. Filter out "BotPoke"
    filtered = filter_out_botpoke(lines)

    # 4. Count remaining
    remaining_count = len(filtered)

    # 5. list of unique IPs
    unique_ips = extract_unique_ips(filtered)

    # Report
    removed = total_lines - remaining_count
    print("=== access.log analysis summary ===")
    print(f"File: {log_path}")
    print(f"Total lines in file: {total_lines}")
    print(f"Lines removed containing 'BotPoke': {removed}")
    print(f"Remaining (non-BotPoke) lines: {remaining_count}")
    print(f"Unique IPs among remaining lines: {len(unique_ips)}")
    print("\nUnique IPs:")
    for ip in unique_ips:
        print(ip)


if __name__ == "__main__":
    main()
