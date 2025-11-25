"""
Gunicorn configuration file for production deployment.

This configuration optimizes Gunicorn for production workloads with:
- Async worker support via gevent
- Proper timeouts and connection handling
- Access and error logging
- Health check endpoint exclusion from logs
- Graceful restart support
"""

import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'gevent'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5

# Restart workers gracefully
graceful_timeout = 30
preload_app = False

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = os.getenv('LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Exclude health checks from access log to reduce noise
def skip_health_check(request):
    """Skip logging for health check endpoints."""
    return request.path in ['/health/liveness', '/health/readiness']

accesslog_filters = {
    'skip_health_check': skip_health_check
}

# Process naming
proc_name = 'privasee-bi-saas'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if using gunicorn as HTTPS termination)
# In production, use Nginx/Traefik for SSL termination
# keyfile = '/path/to/key.pem'
# certfile = '/path/to/cert.pem'

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Privasee BI SaaS starting up...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading workers...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Privasee BI SaaS ready. Workers: {workers}, Port: {bind}")

def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} received ABORT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    pass

def child_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"Worker {worker.pid} exited")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info(f"Workers changed from {old_value} to {new_value}")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Privasee BI SaaS shutting down...")
