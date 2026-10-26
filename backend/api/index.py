"""
api/index.py

Vercel Serverless Function entry point for the FastAPI backend.
Exposes the initialized ASGI application instance 'app'.
"""
from app.main import app
