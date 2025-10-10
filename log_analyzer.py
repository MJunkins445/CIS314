import argparse
import re
from collections import OrderedDict
from pathlib import Path

_IP_CANDIDATE = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b")

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze log file entries, filtering out BotPoke lines and listing unique IPv4 addresses.",
    )
    parser.add_argument(
        "log_file",
        type=Path,
        help="Path to the log file to analyze.",
    )
    return parser.parse_args()

def _is_valid_ipv4(candidate: str) -> bool:
    parts = candidate.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part:
            return False
        if len(part) > 1 and part[0] == "0":
            return False
        try:
            value = int(part)
        except ValueError:
            return False
        if value < 0 or value > 255:
            return False
    return True

def analyze_log(path: Path) -> tuple[int, list[str]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise SystemExit(f"Log file not found: {path}")
    except OSError as exc:
        raise SystemExit(f"Unable to read log file: {exc}")

    filtered = [line for line in lines if "BotPoke" not in line]

    unique_ips: "OrderedDict[str, None]" = OrderedDict()
    for line in filtered:
        for match in _IP_CANDIDATE.finditer(line):
            ip = match.group(1)
            if _is_valid_ipv4(ip) and ip not in unique_ips:
                unique_ips[ip] = None

    return len(filtered), list(unique_ips.keys())

def main() -> None:
    args = _parse_args()
    count, ips = analyze_log(args.log_file)
    print(f"Remaining log entries: {count}")
    if ips:
        print("Unique IP addresses:")
        for ip in ips:
            print(f" - {ip}")
    else:
        print("No IP addresses found.")

if __name__ == "__main__":
    main()
