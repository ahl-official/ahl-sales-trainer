"""
Gunicorn configuration for Render deployment
"""
import os
import multiprocessing

# Bind to PORT from environment (Render provides this)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Workers = (2 x CPU cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1
workers = min(workers, 4)  # Cap at 4 for free/starter tier

# Threads per worker
threads = 4

# Timeout for requests (seconds)
timeout = 120

# Worker class
worker_class = 'sync'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Keep-alive connections
keepalive = 5

# Graceful timeout
graceful_timeout = 30

# Max requests before worker restart (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 100
