#!/usr/bin/env python3
"""
Run the Sea Street Detailing Meta Ads Agent.

Main entry point for the AI agent. Fetches data from Meta API,
sends it to Claude for analysis, and outputs recommendations.

Usage:
    python scripts/run_agent.py                  # Full daily analysis
    python scripts/run_agent.py --quick           # Quick health check
    python scripts/run_agent.py --test-brain      # Test Claude API only
    python scripts/run_agent.py --test-meta       # Test Meta API only
    python scripts/run_agent.py --date-range last_14d  # Custom date range
"""

import sys
import os
import argparse
import logging
import smtplib
import socket
import time
import requests.exceptions
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# Add project root to path so imports work from scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from config.settings import get_settings
from agent.brain import AgentBrain
from agent.memory import AgentMemory
from agent.core import MetaAdsAgent
from data_layer.meta_client import MetaAPIClient


def wait_for_network(max_wait: int = 120, check_interval: int = 5):
    """
    Wait for network connectivity before proceeding.

    When macOS wakes from sleep and launchd fires a missed job,
    WiFi may not be connected yet. This waits until DNS resolves.

    Args:
        max_wait: Maximum seconds to wait for network
        check_interval: Seconds between checks
    """
    logger = logging.getLogger(__name__)
    hosts_to_check = ["graph.facebook.com", "api.anthropic.com"]
    elapsed = 0

    while elapsed < max_wait:
        for host in hosts_to_check:
            try:
                socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)
                logger.info(f"Network ready - resolved {host} after {elapsed}s")
                return True
            except socket.gaierror:
                pass

        logger.info(f"Waiting for network... ({elapsed}/{max_wait}s)")
        time.sleep(check_interval)
        elapsed += check_interval

    logger.error(f"Network not available after {max_wait}s")
    return False


def setup_logging(log_level: str = "INFO", log_dir: Path = None):
    """Configure logging for the agent."""
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def test_brain():
    """Test that the Claude API connection works."""
    print("\n--- Testing Agent Brain (Claude API) ---\n")

    try:
        brain = AgentBrain()
        print(f"Model: {brain.model}")

        response = brain.reason_about(
            "You are being tested. Respond with exactly: BRAIN CONNECTED SUCCESSFULLY"
        )
        print(f"Response: {response}")

        if "BRAIN CONNECTED" in response:
            print("\nBrain test PASSED")
            return True
        else:
            print("\nBrain test FAILED - unexpected response")
            return False

    except Exception as e:
        print(f"\nBrain test FAILED: {e}")
        return False


def test_meta():
    """Test that the Meta API connection works."""
    print("\n--- Testing Meta API Connection ---\n")

    try:
        client = MetaAPIClient()
        print(f"Account: {client.ad_account_id}")

        info = client.get_account_info()
        print(f"Account Name: {info.get('name', 'Unknown')}")
        print(f"Currency: {info.get('currency', 'Unknown')}")
        print(f"Timezone: {info.get('timezone_name', 'Unknown')}")

        campaigns = client.get_campaigns()
        print(f"Total campaigns found: {len(campaigns)}")
        for c in campaigns[:5]:
            print(f"  - {c.name} ({c.status})")

        print("\nMeta API test PASSED")
        return True

    except Exception as e:
        print(f"\nMeta API test FAILED: {e}")
        print("\nCommon fixes:")
        print("  1. Regenerate your access token in Meta Business Suite")
        print("  2. Check that META_ACCESS_TOKEN is set in .env")
        print("  3. Verify ad account ID is correct")
        return False


def run_quick_check(agent: MetaAdsAgent):
    """Run a quick health check."""
    print("\n--- Quick Health Check ---\n")

    try:
        result = agent.run_quick_check()
        print(result)
    except Exception as e:
        print(f"Quick check failed: {e}")
        raise


def send_email(report: str, settings):
    """Send the report via email."""
    logger = logging.getLogger(__name__)

    if not settings.email_to or not settings.smtp_user or not settings.smtp_password:
        logger.warning("Email not configured. Set EMAIL_TO, SMTP_USER, SMTP_PASSWORD in .env")
        return False

    today = datetime.now().strftime('%Y-%m-%d')

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Sea Street Ads Report - {today}"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.email_to

    # Plain text version (the markdown report)
    msg.attach(MIMEText(report, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.email_to, msg.as_string())

        logger.info(f"Report emailed to {settings.email_to}")
        print(f"Report emailed to {settings.email_to}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        print(f"Failed to send email: {e}")
        return False


def run_daily_analysis(agent: MetaAdsAgent, date_range: str = "last_7d", email: bool = False):
    """Run the full daily analysis."""
    print(f"\n{'='*60}")
    print(f"  Sea Street Detailing - Meta Ads AI Agent")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Analyzing: {date_range}")
    print(f"{'='*60}\n")

    try:
        result = agent.run_daily_analysis(date_range=date_range)

        # Generate and print the report
        report = agent.generate_report(result)
        print(report)

        # Save report to file
        settings = get_settings()
        export_dir = Path(settings.report_output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        report_path = export_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path.write_text(report)
        print(f"\nReport saved to: {report_path}")

        # Show recommendation summary
        if result.recommendations:
            print(f"\n--- {len(result.recommendations)} Recommendations ---")
            for i, rec in enumerate(result.recommendations, 1):
                confidence = rec.get("confidence", "?")
                risk = rec.get("risk", "?")
                print(f"  {i}. [{confidence}/{risk}] {rec.get('action', 'Unknown')}")
        else:
            print("\nNo specific recommendations generated.")

        # Send email if requested
        if email:
            send_email(report, settings)

        return result

    except Exception as e:
        print(f"\nAnalysis failed: {e}")
        logging.getLogger(__name__).exception("Analysis failed")
        raise


def main():
    parser = argparse.ArgumentParser(description="Sea Street Detailing Meta Ads AI Agent")
    parser.add_argument("--quick", action="store_true", help="Run quick health check")
    parser.add_argument("--test-brain", action="store_true", help="Test Claude API connection")
    parser.add_argument("--test-meta", action="store_true", help="Test Meta API connection")
    parser.add_argument("--date-range", default="last_7d",
                        choices=["last_3d", "last_7d", "last_14d", "last_30d"],
                        help="Date range for analysis")
    parser.add_argument("--email", action="store_true",
                        help="Email the report after analysis")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Don't execute actions (default: true)")
    args = parser.parse_args()

    # Load settings
    try:
        settings = get_settings()
    except Exception as e:
        print(f"Failed to load settings: {e}")
        print("Make sure .env file exists with required values. See .env.example")
        sys.exit(1)

    # Setup logging
    setup_logging(settings.log_level, Path(settings.log_dir))
    logger = logging.getLogger(__name__)

    # Handle test modes
    if args.test_brain:
        success = test_brain()
        sys.exit(0 if success else 1)

    if args.test_meta:
        success = test_meta()
        sys.exit(0 if success else 1)

    # Wait for network (critical for wake-from-sleep scenarios)
    logger.info("Checking network connectivity...")
    if not wait_for_network(max_wait=120, check_interval=5):
        logger.error("No network connectivity. Aborting.")
        print("ERROR: No network connectivity after 2 minutes. Agent cannot run.")
        sys.exit(1)

    # Retry logic for the full agent run
    max_retries = 3
    retry_delay = 30  # seconds between retries

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Agent run attempt {attempt}/{max_retries}")

            # Initialize components for full run
            print("Initializing agent components...")

            meta_client = MetaAPIClient()
            logger.info("Meta API client initialized")

            brain = AgentBrain()
            logger.info("Agent brain initialized")

            db_path = str(settings.database_path)
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            memory = AgentMemory(db_path=db_path)
            logger.info("Agent memory initialized")

            agent = MetaAdsAgent(
                meta_client=meta_client,
                brain=brain,
                memory=memory,
                dry_run=args.dry_run,
            )
            logger.info("Agent ready")

            # Run the requested mode
            if args.quick:
                run_quick_check(agent)
            else:
                run_daily_analysis(agent, date_range=args.date_range, email=args.email)

            # If we get here, it succeeded
            break

        except (ConnectionError, requests.exceptions.ConnectionError, socket.gaierror, OSError) as e:
            logger.warning(f"Attempt {attempt} failed (network error): {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")
                print(f"ERROR: Agent failed after {max_retries} attempts: {e}")
                sys.exit(1)

        except Exception as e:
            # Non-network errors should not retry
            logger.exception(f"Agent failed with non-recoverable error: {e}")
            print(f"ERROR: Agent failed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
