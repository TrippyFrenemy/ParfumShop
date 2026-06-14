from starlette.requests import Request


async def get_real_ip(request: Request) -> str:
    # X-Real-IP is set by nginx to the actual client IP and is safe to trust
    # since port 8000 is only bound to 127.0.0.1 and not reachable externally
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        return x_real_ip
    if "x-forwarded-for" in request.headers:
        return request.headers["x-forwarded-for"].split(",")[0].strip()
    return request.client.host