"""
TransIQ Backend - CLI Entrypoint
Usage:
    python main.py                  # Run dev server
    python main.py --host 0.0.0.0   # Run on all interfaces
    python main.py --port 8001      # Custom port
"""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="TransIQ Backend Server")
    parser.add_argument("--host", default="localhost", help="Bind host (default: localhost)")
    parser.add_argument("--port", type=int, default=8001, help="Bind port (default: 8001)")
    parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="Disable auto-reload")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
