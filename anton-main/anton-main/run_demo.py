"""Launch Anton against the E2E stub server for a quick test drive (no API key needed)."""

import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from tests.e2e.stub_server import StubServer

stub = StubServer()
stub.start()

# Queue several canned responses so Anton has something to say
stub.queue_text("Hello Boss! I'm Anton running in demo mode against the stub server. Ask me anything and I'll respond with pre-queued messages.")
stub.queue_text("Sure thing! I can help with that. In a real session I'd be powered by an actual LLM, but right now I'm returning scripted responses from the stub server.")
stub.queue_text("Here's an example: I could write code, analyze data, or answer questions. This is response #3 from the stub queue.")
stub.queue_text("That's a great question! Unfortunately I've run out of scripted responses after this one. To get real AI responses, configure a real API key with `anton setup`.")
stub.queue_text("I'm still here! Each message you send consumes one queued response from the stub.")

print(f"\n  Stub LLM server running at {stub.base_url}\n")

# Set env vars to bypass onboarding and point at the stub
os.environ.update({
    "ANTON_TERMS_CONSENT": "true",
    "ANTON_PLANNING_PROVIDER": "openai-compatible",
    "ANTON_CODING_PROVIDER": "openai-compatible",
    "ANTON_OPENAI_BASE_URL": stub.base_url,
    "ANTON_OPENAI_API_KEY": "test-key-e2e",
    "ANTON_PLANNING_MODEL": "gpt-test",
    "ANTON_CODING_MODEL": "gpt-test",
    "ANTON_ANALYTICS_ENABLED": "false",
    "ANTON_DISABLE_AUTOUPDATES": "true",
    "ANTON_MINDS_ENABLED": "false",
    "ANTON_MEMORY_ENABLED": "false",
})

# Now import and run the CLI
from anton.cli import app
try:
    app()
except (KeyboardInterrupt, EOFError):
    pass
finally:
    stub.stop()
    print("\n  Stub server stopped.")
