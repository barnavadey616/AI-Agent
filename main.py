"""
Main entry point for production deployment (Render, Heroku, Cloud Run, Docker).
Reads PORT environment variable and serves the TaskFlow FastAPI app via Uvicorn.
"""

import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Render binds on 0.0.0.0
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
