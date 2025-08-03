import subprocess, json, asyncio


async def run_cli(opportunity: str, trace_id: str):
    proc = await asyncio.create_subprocess_exec(
        "python",
        "main.py",
        opportunity,
        trace_id,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if err:
        print("Python script stderr:", err.decode()[:300])
    try:
        start = out.rfind(b"{")
        return json.loads(out[start:]) if start != -1 else {}
    except Exception:
        return {}
