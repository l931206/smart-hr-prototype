"""Exercise the remote Smart HR MCP flow against a demo environment.

The script obtains a short-lived mock-central Bearer token, discovers tools,
previews a leave request, submits it once, and withdraws the resulting request.
It is intended for local/demo verification only.
"""

import argparse
import asyncio

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def run(base_url: str, external_user_id: str):
    async with httpx2.AsyncClient(follow_redirects=True) as login_client:
        response = await login_client.post(
            f"{base_url}/api/mock-central/login/",
            json={"external_user_id": external_user_id},
        )
        response.raise_for_status()
        token = response.json()["access_token"]

    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True,
    ) as authorized_client:
        transport = streamable_http_client(f"{base_url}/mcp", http_client=authorized_client)
        async with Client(transport, raise_exceptions=True) as client:
            tools = await client.list_tools()
            print("tools:", [tool.name for tool in tools.tools])

            me = await client.call_tool("get_current_user", {})
            print("current_user:", me.structured_content)

            preview = await client.call_tool("preview_leave_request", {
                "leave_type": "公假",
                "start_date": "2026-09-01",
                "end_date": "2026-09-01",
                "start_time": "上午",
                "end_time": "下午",
                "reason": "MCP 端對端測試",
            })
            print("preview:", preview.structured_content)
            draft_id = preview.structured_content["draft_id"]

            submitted = await client.call_tool("submit_leave_request", {"draft_id": draft_id})
            print("submitted:", submitted.structured_content)
            request_id = submitted.structured_content["request"]["request_id"]

            withdrawn = await client.call_tool("withdraw_leave_request", {"request_id": request_id})
            print("withdrawn:", withdrawn.structured_content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    parser.add_argument("--external-user-id", default="central-employee-001")
    args = parser.parse_args()
    asyncio.run(run(args.base_url.rstrip("/"), args.external_user_id))


if __name__ == "__main__":
    main()
