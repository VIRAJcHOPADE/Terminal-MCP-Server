
"""
terminal_server_sse.py

MCP SSE server exposing terminal and file tools.
"""

import os
import subprocess

from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import PlainTextResponse

import uvicorn


# Initialize MCP
mcp = FastMCP("terminal")

# Workspace directory
DEFAULT_WORKSPACE = os.path.expanduser("~/mcp/workspace")
os.makedirs(DEFAULT_WORKSPACE, exist_ok=True)


# -----------------------------
# TOOL 1 : run_command
# -----------------------------
@mcp.tool()
async def run_command(command: str) -> str:
    """
    Execute shell command inside workspace.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=DEFAULT_WORKSPACE,
            capture_output=True,
            text=True
        )

        return result.stdout or result.stderr or "Command executed."

    except Exception as e:
        return str(e)


# -----------------------------
# TOOL 2 : add_numbers
# -----------------------------
@mcp.tool()
async def add_numbers(a: float, b: float) -> float:
    """
    Add two numbers.
    """
    return a + b


# -----------------------------
# TOOL 3 : write_file
# -----------------------------
@mcp.tool()
async def write_file(filename: str, content: str) -> str:
    """
    Save content to a file in workspace.
    """
    try:
        path = os.path.join(DEFAULT_WORKSPACE, filename)

        with open(path, "w") as f:
            f.write(content)

        return f"File '{filename}' saved successfully."

    except Exception as e:
        return str(e)


# -----------------------------
# Create Starlette app
# -----------------------------
def create_starlette_app(mcp_server: Server, debug: bool = False) -> Starlette:

    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):

        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):

            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

        return PlainTextResponse("SSE connection closed")

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


# -----------------------------
# Run server
# -----------------------------
if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(description="Run MCP SSE server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8081)

    args = parser.parse_args()

    mcp_server = mcp._mcp_server

    app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )
