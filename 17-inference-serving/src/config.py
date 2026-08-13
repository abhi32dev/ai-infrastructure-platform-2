from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
SERVER_PORT = 8090
SERVER_HOST = "127.0.0.1"

CONCURRENT_REQUESTS = 8       # simulated concurrent users hitting the server
MAX_TOKENS = 64
PROMPT = "Explain what a load balancer does in exactly two sentences."
