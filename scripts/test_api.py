#!/usr/bin/env python3
"""Test script for KnowledgeEnroll APIs.

Usage:
    python test_api.py [--admin-url URL] [--embedding-url URL] [--verbose]
"""
import argparse
import json
import requests
import sys
from datetime import datetime


def test_health(base_url: str, name: str) -> bool:
    """Test health endpoint."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.ok:
            data = response.json()
            print(f"  [{name}] Health: {data.get('status', 'unknown')}")
            return data.get('status') == 'healthy'
        else:
            print(f"  [{name}] Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  [{name}] Health check error: {e}")
        return False


def test_admin_api(base_url: str, verbose: bool = False) -> dict:
    """Test Admin API endpoints."""
    results = {"passed": 0, "failed": 0, "tests": []}

    def log_test(name: str, passed: bool, details: str = ""):
        results["tests"].append({"name": name, "passed": passed, "details": details})
        if passed:
            results["passed"] += 1
            print(f"    PASS: {name}")
        else:
            results["failed"] += 1
            print(f"    FAIL: {name} - {details}")

    print("\n  Testing Admin API...")

    # Test API info
    try:
        response = requests.get(f"{base_url}/api/v1", timeout=5)
        log_test("API Info", response.ok, f"Status: {response.status_code}")
    except Exception as e:
        log_test("API Info", False, str(e))

    # Test channel stats
    try:
        response = requests.get(f"{base_url}/api/v1/channels/stats", timeout=5)
        if response.ok:
            data = response.json()
            log_test("Channel Stats", True, f"Total: {data.get('total', 0)}")
            if verbose:
                print(f"      Domains: {json.dumps(data.get('by_domain', []), indent=2)}")
        else:
            log_test("Channel Stats", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Channel Stats", False, str(e))

    # Test list channels
    try:
        response = requests.get(f"{base_url}/api/v1/channels?limit=5", timeout=5)
        if response.ok:
            data = response.json()
            log_test("List Channels", True, f"Retrieved: {len(data.get('channels', []))}")
        else:
            log_test("List Channels", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("List Channels", False, str(e))

    # Test pipeline stats
    try:
        response = requests.get(f"{base_url}/api/v1/pipeline/stats", timeout=5)
        if response.ok:
            data = response.json()
            log_test("Pipeline Stats", True, f"Total: {data.get('total', 0)}")
        else:
            log_test("Pipeline Stats", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Pipeline Stats", False, str(e))

    # Test create channel (with cleanup)
    test_handle = f"test_channel_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    channel_id = None
    try:
        response = requests.post(
            f"{base_url}/api/v1/channels",
            json={
                "youtube_handle": test_handle,
                "name": "Test Channel",
                "domain": "general"
            },
            timeout=5
        )
        if response.status_code == 201:
            data = response.json()
            channel_id = data.get('id')
            log_test("Create Channel", True, f"ID: {channel_id}")
        else:
            log_test("Create Channel", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Create Channel", False, str(e))

    # Test update channel
    if channel_id:
        try:
            response = requests.put(
                f"{base_url}/api/v1/channels/{channel_id}",
                json={"name": "Updated Test Channel"},
                timeout=5
            )
            log_test("Update Channel", response.ok, f"Status: {response.status_code}")
        except Exception as e:
            log_test("Update Channel", False, str(e))

        # Cleanup: delete test channel
        try:
            response = requests.delete(f"{base_url}/api/v1/channels/{channel_id}", timeout=5)
            log_test("Delete Channel", response.ok, f"Status: {response.status_code}")
        except Exception as e:
            log_test("Delete Channel", False, str(e))

    return results


def test_embedding_api(base_url: str, verbose: bool = False) -> dict:
    """Test Embedding API endpoints."""
    results = {"passed": 0, "failed": 0, "tests": []}

    def log_test(name: str, passed: bool, details: str = ""):
        results["tests"].append({"name": name, "passed": passed, "details": details})
        if passed:
            results["passed"] += 1
            print(f"    PASS: {name}")
        else:
            results["failed"] += 1
            print(f"    FAIL: {name} - {details}")

    print("\n  Testing Embedding API...")

    # Test API info
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        log_test("API Info", response.ok, f"Status: {response.status_code}")
    except Exception as e:
        log_test("API Info", False, str(e))

    # Test stats
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=5)
        if response.ok:
            data = response.json()
            log_test("Stats", True, f"Videos: {data.get('videos', 0)}, Segments: {data.get('segments', 0)}")
        else:
            log_test("Stats", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Stats", False, str(e))

    # Test embed endpoint (dry run with minimal data)
    try:
        response = requests.post(
            f"{base_url}/api/embed",
            json={
                "video_id": "test123",
                "title": "Test Video",
                "transcript": "This is a test transcript for API testing.",
                "channel_handle": "test",
                "skip_embeddings": True
            },
            timeout=10
        )
        if response.ok:
            data = response.json()
            log_test("Embed Video", data.get('success', False), f"Segments: {data.get('segment_count', 0)}")
        else:
            log_test("Embed Video", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Embed Video", False, str(e))

    # Test get video
    try:
        response = requests.get(f"{base_url}/api/video/test123", timeout=5)
        if response.ok:
            data = response.json()
            log_test("Get Video", data.get('success', False), f"Found: {bool(data.get('video'))}")
        else:
            # 404 is acceptable for non-existent video
            log_test("Get Video", response.status_code == 404, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Get Video", False, str(e))

    return results


def main():
    parser = argparse.ArgumentParser(description='Test KnowledgeEnroll APIs')
    parser.add_argument('--admin-url', default='http://10.0.0.33:5020', help='Admin API base URL')
    parser.add_argument('--embedding-url', default='http://10.0.0.33:5030', help='Embedding API base URL')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--skip-admin', action='store_true', help='Skip Admin API tests')
    parser.add_argument('--skip-embedding', action='store_true', help='Skip Embedding API tests')
    args = parser.parse_args()

    print("=" * 60)
    print("KnowledgeEnroll API Test Suite")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    # Health checks
    print("\n[1] Health Checks")
    admin_healthy = False
    embedding_healthy = False

    if not args.skip_admin:
        admin_healthy = test_health(args.admin_url, "Admin")
    if not args.skip_embedding:
        embedding_healthy = test_health(args.embedding_url, "Embedding")

    # Admin API tests
    if not args.skip_admin:
        print("\n[2] Admin API Tests")
        if admin_healthy:
            admin_results = test_admin_api(args.admin_url, args.verbose)
            total_passed += admin_results["passed"]
            total_failed += admin_results["failed"]
        else:
            print("  Skipping (service unhealthy)")

    # Embedding API tests
    if not args.skip_embedding:
        print("\n[3] Embedding API Tests")
        if embedding_healthy:
            embedding_results = test_embedding_api(args.embedding_url, args.verbose)
            total_passed += embedding_results["passed"]
            total_failed += embedding_results["failed"]
        else:
            print("  Skipping (service unhealthy)")

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    sys.exit(0 if total_failed == 0 else 1)


if __name__ == '__main__':
    main()
