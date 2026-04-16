import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from opus_clone.config import get_settings

settings = get_settings()

broker = RedisBroker(url=settings.redis_broker_url)
broker.add_middleware(Retries(max_retries=3))
broker.add_middleware(TimeLimit(time_limit=600_000))  # 10 min
broker.add_middleware(AgeLimit(max_age=3_600_000))  # 1 hour

dramatiq.set_broker(broker)

# Import actors to register them
from opus_clone.workers.ingest import ingest_video  # noqa: F401, E402
from opus_clone.workers.process import process_video  # noqa: F401, E402
