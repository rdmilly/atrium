import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router, listen_pg_notify
from .public_pages import router as public_router
from .mcp_server import mcp
from .settings import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("atrium")

# Build the FastMCP ASGI app once so we can chain its lifespan into ours.
mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # FastMCP requires its lifespan to run inside the parent app, otherwise
    # the StreamableHTTPSessionManager task group is never initialized.
    async with mcp_app.lifespan(app):
        listener = asyncio.create_task(listen_pg_notify())
        logger.info("atrium service started, pg notify listener active")
        try:
            yield
        finally:
            listener.cancel()


app = FastAPI(title="Atrium", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://atrium.millyweb.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(public_router)
app.mount("/mcp", mcp_app)
