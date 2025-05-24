import pytest_asyncio
import redis.asyncio as redis
from fastapi.testclient import TestClient
from main import app, REDIS_HOSTNAME, REDIS_PORT


@pytest_asyncio.fixture
async def redis_client():
    # Setup Redis connection
    rc = redis.Redis(host=REDIS_HOSTNAME, port=REDIS_PORT, db=0, decode_responses=True)

    # Clear database before test
    await rc.flushdb()
    yield rc

    # Clear database after test
    await rc.flushdb()
    await rc.close()


@pytest_asyncio.fixture(scope='session')
def client():
    with TestClient(app) as test_client:
        yield test_client
