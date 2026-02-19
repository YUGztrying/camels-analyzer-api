"""Entrypoint for Railway deployment.

Reads PORT from environment (Railway sets this dynamically)
and starts uvicorn on that port. Avoids shell expansion issues
with ${PORT:-8000} in Dockerfile CMD or railway.toml startCommand.
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
