"""
SecureRotate AI - Scheduled Background Jobs Module
Uses APScheduler AsyncIOScheduler to run daily credential expiry scans.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.db.session import AsyncSessionLocal
from app.services.expiry_monitor import run_expiry_scan

logger = logging.getLogger("securerotate.scheduler")

scheduler = AsyncIOScheduler()


async def scheduled_daily_expiry_check():
    """Daily scheduled background job executing credential expiry scanning."""
    logger.info("Starting scheduled daily credential expiry scan...")
    async with AsyncSessionLocal() as db:
        try:
            result = await run_expiry_scan(db)
            logger.info(
                f"Scheduled expiry scan completed: checked {result['checked_credentials']} credentials, "
                f"created {result['notifications_created']} notifications."
            )
        except Exception as e:
            logger.error(f"Error executing scheduled expiry scan: {e}")


def start_scheduler():
    """Initializes and starts the background AsyncIOScheduler."""
    if not scheduler.running:
        scheduler.add_job(
            scheduled_daily_expiry_check,
            "interval",
            hours=1,
            id="daily_expiry_scan",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Background AsyncIOScheduler started successfully (hourly interval).")


def shutdown_scheduler():
    """Shuts down the background scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background AsyncIOScheduler shut down.")
