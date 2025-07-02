from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from .rss_handler import FeedBridge


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.feed_bridge = FeedBridge()

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/bridge/")
def _(
    source_url: str,
    request: Request,
    num: int | None = None,
):
    xml_feed = request.app.state.feed_bridge.parse(source_url, num=num)
    return Response(content=xml_feed, media_type="application/xml")
