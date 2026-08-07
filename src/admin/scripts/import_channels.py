#!/usr/bin/env python3
"""Import channels from CSV file into PostgreSQL database.

Usage:
    python import_channels.py [--csv path/to/channels.csv] [--dry-run]

Environment variables:
    KNOWLEDGE_DB_HOST - PostgreSQL host (default: 10.0.0.33)
    KNOWLEDGE_DB_PORT - PostgreSQL port (default: 5010)
    KNOWLEDGE_DB_NAME - Database name (default: knowledge)
    KNOWLEDGE_DB_USER - Database user (default: knowledge)
    KNOWLEDGE_DB_PASSWORD - Database password
"""
import argparse
import csv
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import execute_values


def get_db_config():
    """Get database configuration from environment."""
    return {
        'host': os.getenv('KNOWLEDGE_DB_HOST', '10.0.0.33'),
        'port': os.getenv('KNOWLEDGE_DB_PORT', '5010'),
        'dbname': os.getenv('KNOWLEDGE_DB_NAME', 'knowledge'),
        'user': os.getenv('KNOWLEDGE_DB_USER', 'knowledge'),
        'password': os.getenv('KNOWLEDGE_DB_PASSWORD', ''),
    }


def parse_csv(csv_path: str) -> list[dict]:
    """Parse channels CSV file."""
    channels = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip empty rows
            if not row.get('youtube_handle'):
                continue

            channel = {
                'youtube_handle': row['youtube_handle'].strip(),
                'name': row['name'].strip(),
                'domain': row.get('domain', 'general').strip().lower(),
                'authority_score': int(row.get('authority_score', 5)),
                'relevance_score': int(row.get('relevance_score', 5)),
                'ingestion_mode': row.get('ingestion_mode', 'auto').strip().lower(),
                'description': row.get('notes', '').strip() or None,
            }

            # Validate scores
            channel['authority_score'] = max(1, min(10, channel['authority_score']))
            channel['relevance_score'] = max(1, min(10, channel['relevance_score']))

            # Validate domain
            valid_domains = ['ai-tech', 'business', 'mindset', 'health', 'political', 'faith', 'general']
            if channel['domain'] not in valid_domains:
                print(f"Warning: Invalid domain '{channel['domain']}' for {channel['youtube_handle']}, using 'general'")
                channel['domain'] = 'general'

            # Validate ingestion mode
            valid_modes = ['auto', 'review', 'guest_monitor', 'paused']
            if channel['ingestion_mode'] not in valid_modes:
                print(f"Warning: Invalid mode '{channel['ingestion_mode']}' for {channel['youtube_handle']}, using 'auto'")
                channel['ingestion_mode'] = 'auto'

            channels.append(channel)

    return channels


def import_channels(channels: list[dict], dry_run: bool = False) -> tuple[int, int]:
    """Import channels into database.

    Returns:
        Tuple of (created_count, skipped_count)
    """
    if dry_run:
        print("\n[DRY RUN] Would import the following channels:")
        for c in channels:
            print(f"  - {c['youtube_handle']}: {c['name']} ({c['domain']})")
        return len(channels), 0

    config = get_db_config()
    conn = psycopg2.connect(**config)

    try:
        cursor = conn.cursor()

        # Prepare values for batch insert
        insert_query = """
            INSERT INTO channels (
                youtube_handle, name, domain,
                authority_score, relevance_score,
                ingestion_mode, description
            )
            VALUES %s
            ON CONFLICT (youtube_handle) DO NOTHING
            RETURNING youtube_handle
        """

        values = [
            (
                c['youtube_handle'],
                c['name'],
                c['domain'],
                c['authority_score'],
                c['relevance_score'],
                c['ingestion_mode'],
                c['description']
            )
            for c in channels
        ]

        # Execute batch insert
        from psycopg2.extras import execute_values
        result = execute_values(
            cursor,
            insert_query,
            values,
            template="(%s, %s, %s, %s, %s, %s, %s)",
            fetch=True
        )

        created_count = len(result) if result else 0
        skipped_count = len(channels) - created_count

        conn.commit()

        return created_count, skipped_count

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Import channels from CSV to PostgreSQL')
    parser.add_argument(
        '--csv',
        default='../../db/seed/channels.csv',
        help='Path to channels CSV file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview import without making changes'
    )
    args = parser.parse_args()

    # Resolve CSV path
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = Path(__file__).parent / csv_path

    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)

    print(f"Reading channels from: {csv_path}")

    # Parse CSV
    channels = parse_csv(str(csv_path))
    print(f"Found {len(channels)} channels in CSV")

    if not channels:
        print("No channels to import.")
        sys.exit(0)

    # Show summary by domain
    domains = {}
    for c in channels:
        domains[c['domain']] = domains.get(c['domain'], 0) + 1

    print("\nChannels by domain:")
    for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
        print(f"  {domain}: {count}")

    # Import
    created, skipped = import_channels(channels, args.dry_run)

    if args.dry_run:
        print(f"\n[DRY RUN] Would create {len(channels)} channels")
    else:
        print(f"\nImport complete:")
        print(f"  Created: {created}")
        print(f"  Skipped (already exist): {skipped}")


if __name__ == '__main__':
    main()
