import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from .rss_handler import FeedBridge
from .daily_aggregator import DailyAggregator

# Configure logging at the entry point
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.feed_bridge = FeedBridge()
    app.state.daily_aggregator = DailyAggregator()

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/extract/")
def _(
    source_url: str,
    request: Request,
    num: int | None = None,
):
    xml_feed = request.app.state.feed_bridge.parse(source_url, num=num)
    return Response(content=xml_feed, media_type="application/xml")


@app.get("/daily_summary/")
def _(
    source_url: str,
    request: Request,
    num: int | None = None,
):
    xml_feed = request.app.state.daily_aggregator.process_feed(source_url, num=num)
    return Response(content=xml_feed, media_type="application/xml")
