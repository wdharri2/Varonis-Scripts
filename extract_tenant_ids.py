#!/usr/bin/env python3
import argparse
import csv
import os
import sys

from numpy import unique_values

def main():
    # Set up command-line argument behavior
    parser = argparse.ArgumentParser(
        description="Extract unique tenant_id values from a CSV, print comma-separated, then delete the CSV."
    )
    parser.add_argument("csv_path", help="Path to the input CSV file")
    args = parser.parse_args()

    csv_path = args.csv_path

    # validation
    if not os.path.isfile(csv_path):
        print(f"Error: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    unique_values = []
    seen = set()
    tenant_id_headers = None

    try:
        with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f) # Use DictReader for header-based access
            if reader.fieldnames is None: # No header row
                print("Error: CSV appears to have no header row.", file=sys.stderr)
                sys.exit(1)

            # Identify all columns named 'tenant_id' (case-insensitive)
            tenant_id_headers = [
                h for h in reader.fieldnames if h is not None and h.strip().lower() == "tenant_id"
            ]

            if not tenant_id_headers:
                print("Warning: No 'tenant_id' column found. Output will be empty.", file=sys.stderr)

            for row in reader:
                for h in tenant_id_headers:
                    val = row.get(h, "")
                    if val is None:
                        continue
                    val = str(val).strip()
                    if val == "":
                        continue
                    if val not in seen:
                        seen.add(val)
                        unique_values.append(val)


    # Output comma-separated list in chunks of at most 15, with a divider between chunks
    chunk_size = 15
    for i in range(0, len(unique_values), chunk_size):
        chunk = unique_values[i:i + chunk_size]
        print(','.join(chunk))
        if i + chunk_size < len(unique_values):
            print('-----')  # divider between chunks

    except csv.Error as e:
        print(f"Error: Failed to parse CSV: {e}", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError:
        print("Error: Failed to read file with UTF-8 encoding. Try converting the file encoding.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Delete the CSV file after processing
        try:
            os.remove(csv_path)
        except Exception as e:
            # If deletion fails, report but don't change the success of printed output
            print(f"Warning: Could not delete file '{csv_path}': {e}", file=sys.stderr)

if __name__ == "__main__":
    main()