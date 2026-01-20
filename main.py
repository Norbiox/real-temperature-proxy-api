"""Application entry point."""

import uvicorn

from src.real_temperature_proxy_api.core.config import settings


def main():
    """Run the uvicorn server."""
    uvicorn.run(
        "src.real_temperature_proxy_api.app:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=False,
        workers=1,  # Single worker (K8s pattern: scale via pod replicas)
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
