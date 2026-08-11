"""
Step 2: a minimal MCP client — no Claude yet, just you manually driving
the protocol so you can see exactly what a "session" is.

This script will:
  1. start step1_mcp_server_skeleton.py as a subprocess
  2. open a session with it
  3. ask it "what tools do you have?" and print the answer
  4. call the geocode tool yourself and print the result

Run with:
    python step2_client.py
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# TODO 1: describe how to launch the server.
# StdioServerParameters needs two things:
#   - command: the program to run (what do you normally type before the
#     filename when running a python script from the terminal?)
#   - args: a list containing the script's filename as a string
# server_params = StdioServerParameters(command="...", args=["..."])

server_params = StdioServerParameters(command = "python3", args = ["step1_mcp_server_skeleton.py"])


async def main():
    # TODO 2: open the connection.
    # `stdio_client(server_params)` is an async context manager — it
    # starts the server subprocess and gives you back a (read, write)
    # pair of streams. Use `async with ... as (read, write):`
    # async with stdio_client(server_params) as (read, write):
   async with stdio_client(server_params) as (read, write):


        # TODO 3: open a session on top of those streams.
        # ClientSession(read, write) is ALSO an async context manager.
        # This is the actual "conversation" object you'll call methods on.
        # async with ClientSession(read, write) as session:
        async with ClientSession(read, write) as session:

            # TODO 4: every MCP session needs to be initialized before use.
            # There's a method on `session` for this — one word, does
            # what it says. It's an async call, so remember `await`.
            # await session.???()
            await session.initialize()

            # TODO 5: ask the server what tools it has.
            # await session.list_tools() returns an object — print it
            # and see what it looks like.
            tools = await session.list_tools()
            print(tools)


            # TODO 6: call the geocode tool yourself.
            # session.call_tool(name, arguments) takes the tool's name
            # as a string, and a dict of arguments matching its schema
            # (remember `query: str` from the tool you wrote?).
            test_waypoints = [
            (53.387, -2.353),
            (53.393, -2.357),
            (53.391, -2.344),
            (53.383, -2.342),
            (53.380, -2.355),
            ]
            result = await session.call_tool("snap_to_roads", {"waypoints": test_waypoints})
            print(result)



if __name__ == "__main__":
    # TODO 7: run the async main() function.
    # asyncio has a standard entrypoint for exactly this — running one
    # top-level async function from a plain script.
    asyncio.run(main())

