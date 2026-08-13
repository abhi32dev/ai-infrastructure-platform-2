import os

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = "llama3.2:1b"

# Circuit breaker: same shape as the CONDOR bullet — a companion health
# endpoint whose target-health checks pull an unhealthy instance out of
# rotation automatically. Here the "instance" is this serving process's
# connection to its one downstream (Ollama), and "out of rotation" means
# /health reports unhealthy and /generate fast-fails instead of hanging.
FAILURE_THRESHOLD = 3       # consecutive failures before opening the circuit
COOLDOWN_SECONDS = 5         # how long to wait before a half-open retry probe
REQUEST_TIMEOUT_SECONDS = 30
