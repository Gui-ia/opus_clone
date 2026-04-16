import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from opus_clone.logging import get_logger, setup_logging
from opus_clone.scheduler.poller import poll_youtube_channels
from opus_clone.scheduler.pubsub_renewer import renew_pubsub_subscriptions

logger = get_logger("scheduler")


def main():
    setup_logging()
    logger.info("scheduler_starting")

    scheduler = AsyncIOScheduler()

    # Poll YouTube channels every 15 minutes (fallback for PubSubHubbub)
    scheduler.add_job(
        poll_youtube_channels,
        "interval",
        minutes=15,
        id="poll_youtube",
        name="Poll YouTube channels",
        max_instances=1,
    )

    # Renew PubSubHubbub subscriptions every 4 days
    scheduler.add_job(
        renew_pubsub_subscriptions,
        "interval",
        days=4,
        id="renew_pubsub",
        name="Renew PubSub subscriptions",
        max_instances=1,
    )

    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))

    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("scheduler_stopped")


if __name__ == "__main__":
    main()
