from starlette.requests import Request


async def get_real_ip(request: Request) -> str:
    if "x-forwarded-for" in request.headers and request.client.host in ["127.0.0.1", "172.20.0.1"]:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host