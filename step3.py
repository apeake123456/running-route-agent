"""
Step 3: let Claude decide whether/how to call geocode, instead of you
calling it manually.

Run with:
    python3 step3.py
"""

import asyncio
import os
import time
import sys 

from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(command="python3", args=["step1_mcp_server_skeleton.py"])

client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a running route planning assistant with three tools:
1. geocode — resolves a place name into coordinates
2. generate_loop_waypoints — scatters points around a start location for a target distance
3. snap_to_roads — turns those waypoints into a real street-following route

For a request like "give me a route near X", typically call them in that
order: geocode the location first if given a place name (skip if given raw
coordinates), then generate_loop_waypoints, then snap_to_roads on the result.
"""

async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            tools = [
                {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                for t in tools_response.tools
            ]

            user_message = "user_message = Give me a walkable 5k loop starting near Altrincham"
            messages = [{"role": "user", "content": user_message}]

            response = await client.messages.create(
                model="claude-sonnet-5", max_tokens=1000, tools=tools, messages=messages, system = SYSTEM_PROMPT
            )

            print(response.stop_reason)
            print(response.content)

            while response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for n in response.content:
                    if n.type == "tool_use":
                        print(f"calling {n.name} with {n.input}", file=sys.stderr)
                        result = await session.call_tool(n.name, n.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": n.id,
                            "content": result.content[0].text,
                        })

                messages.append({"role": "user", "content": tool_results})

                response = await client.messages.create(
                    model="claude-sonnet-5", max_tokens=1000, system=SYSTEM_PROMPT, tools=tools, messages=messages
                )

            print(response.content)

if __name__ == "__main__":
    asyncio.run(main())