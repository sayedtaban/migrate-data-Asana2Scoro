#!/usr/bin/env python3
"""
This script is used to get the list of user IDs (GIDs) that are not found in the Scoro API
for leaving URLs. It parses log files in the logs directory and extracts GIDs from warning
messages about not finding users.
"""

import re
import os
from pathlib import Path
from typing import Set

def extract_gids_from_logs(logs_dir: str = "logs") -> Set[str]:
    """
    Extract user GIDs from log files where users couldn't be found for leaving URLs.
    
    Args:
        logs_dir: Directory containing log files
        
    Returns:
        Set of unique GIDs that couldn't be found
    """
    gids: Set[str] = set()
    
    # Patterns to match:
    # 1. "Could not find user name for GID: {gid}, leaving URL as-is"
    # 2. "Could not find Scoro user '{user_name}' for GID: {gid}, replacing URL with plain name"
    pattern1 = r'Could not find user name for GID:\s*(\d+),\s*leaving URL'
    pattern2 = r'Could not find Scoro user.*?for GID:\s*(\d+),\s*replacing URL'
    
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        print(f"Error: Logs directory '{logs_dir}' does not exist")
        return gids
    
    log_files = sorted(logs_path.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"Scanning {len(log_files)} log files in '{logs_dir}'...")
    
    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Try pattern 1: "Could not find user name for GID: {gid}, leaving URL"
                    matches1 = re.findall(pattern1, line, re.IGNORECASE)
                    for gid in matches1:
                        gids.add(gid)
                        print(f"  Found in {log_file.name}:{line_num} - GID: {gid} (pattern 1)")
                    
                    # Try pattern 2: "Could not find Scoro user ... for GID: {gid}, replacing URL"
                    matches2 = re.findall(pattern2, line, re.IGNORECASE)
                    for gid in matches2:
                        gids.add(gid)
                        print(f"  Found in {log_file.name}:{line_num} - GID: {gid} (pattern 2)")
        except Exception as e:
            print(f"  Warning: Error reading {log_file.name}: {e}")
    
    return gids


def main():
    """Main function to extract and display GIDs"""
    # Get the logs directory relative to the script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    logs_dir = project_root / "logs"
    
    print("=" * 60)
    print("Extracting user GIDs that couldn't be found for leaving URLs")
    print("=" * 60)
    print()
    
    gids = extract_gids_from_logs(str(logs_dir))
    
    print()
    print("=" * 60)
    print(f"Found {len(gids)} unique user GID(s):")
    print("=" * 60)
    
    if gids:
        # Sort GIDs for consistent output
        sorted_gids = sorted(gids, key=lambda x: int(x) if x.isdigit() else 0)
        for gid in sorted_gids:
            print(gid)
        
        # Also save to a file
        output_file = project_root / "not_found_user_gids.txt"
        with open(output_file, 'w') as f:
            for gid in sorted_gids:
                f.write(f"{gid}\n")
        print()
        print(f"GIDs saved to: {output_file}")
    else:
        print("No GIDs found matching the patterns.")
        print("The log files may not contain the expected warning messages.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
