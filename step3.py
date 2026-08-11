"""
Step 3: let Claude decide whether/how to call geocode, instead of you
calling it manually.

Run with:
    python3 step3.py
"""

import asyncio
import os
import time

from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(command="python3", args=["step1_mcp_server_skeleton.py"])

client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools_response = await session.list_tools()
            tools = [
                {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
                for t in tools_response.tools
            ]

            user_message = "Give me some waypoints for a 5k loop starting at 53.387, -2.353"
            messages = [{"role": "user", "content": user_message}]

            response = await client.messages.create(
                model="claude-sonnet-5", max_tokens=1000, tools=tools, messages=messages
            )

            print(response.stop_reason)
            print(response.content)

            for n in response.content:
                if n.type == "tool_use":
                    try:
                        print("calling tool at", time.strftime("%H:%M:%S"))
                        result = await session.call_tool(n.name, n.input)
                        print("tool returned at", time.strftime("%H:%M:%S"))
                        print("TOOL RESULT:", result)

                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": n.id,
                                "content": result.content[0].text,
                            }],
                        })

                        response = await client.messages.create(
                            model="claude-sonnet-5", max_tokens=1000, tools=tools, messages=messages
                        )
                        print(response.content)
                    except Exception as e:
                        print("SOMETHING FAILED:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())