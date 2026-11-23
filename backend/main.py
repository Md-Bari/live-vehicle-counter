"""FastAPI backend: live vehicle-type detection + line-crossing counting.

Run:  uvicorn main:app --host 0.0.0.0 --port 8001      (from app/backend)
Docs: http://localhost:8001/docs
(Port 8000 is taken by Docker Desktop on this machine.)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

