#!/usr/bin/env python3
"""
Test Meta API Connection

Run this script to verify your Meta API credentials are working correctly.
Make sure you have a .env file with your credentials before running.

Usage:
    python scripts/test_connection.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(project_root / ".env")

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount


def test_connection():
    """Test the Meta API connection and print account info."""

    import os

    access_token = os.getenv("META_ACCESS_TOKEN")
    ad_account_id = os.getenv("META_AD_ACCOUNT_ID")

    if not access_token:
        print("ERROR: META_ACCESS_TOKEN not found in .env file")
        print("Please copy .env.example to .env and add your access token")
        return False

    if not ad_account_id:
        print("ERROR: META_AD_ACCOUNT_ID not found in .env file")
        print("Please add your ad account ID (format: act_XXXXXXXXX)")
        return False

    print(f"Testing connection to ad account: {ad_account_id}")
    print("-" * 50)

    try:
        # Initialize the API
        FacebookAdsApi.init(access_token=access_token)

        # Get account info
        account = AdAccount(ad_account_id)
        account_info = account.api_get(fields=[
            "name",
            "account_id",
            "account_status",
            "currency",
            "timezone_name"
        ])

        print("SUCCESS! Connected to Meta Ads API")
        print("-" * 50)
        print(f"Account Name: {account_info.get('name')}")
        print(f"Account ID: {account_info.get('account_id')}")
        print(f"Status: {account_info.get('account_status')}")
        print(f"Currency: {account_info.get('currency')}")
        print(f"Timezone: {account_info.get('timezone_name')}")

        # Try to get campaigns
        print("-" * 50)
        print("Fetching campaigns...")

        campaigns = account.get_campaigns(fields=["name", "status", "objective"])
        campaign_list = list(campaigns)

        print(f"Found {len(campaign_list)} campaigns:")
        for camp in campaign_list[:5]:  # Show first 5
            print(f"  - {camp.get('name')} ({camp.get('status')})")

        if len(campaign_list) > 5:
            print(f"  ... and {len(campaign_list) - 5} more")

        print("-" * 50)
        print("Connection test PASSED!")
        return True

    except Exception as e:
        print(f"ERROR: {type(e).__name__}")
        print(f"Details: {str(e)}")
        print("-" * 50)
        print("Common issues:")
        print("  1. Invalid access token (may have expired)")
        print("  2. Wrong ad account ID format (should be act_XXXXXXXXX)")
        print("  3. Insufficient permissions on the access token")
        print("  4. Account not linked to the app")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
