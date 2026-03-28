"""
Execution Root interface launching the structural App Factory securely.
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    host_addr = os.environ.get("HOST", "0.0.0.0")
    run_port = int(os.environ.get("PORT", "8080"))
    app.run(debug=True, host=host_addr, port=run_port)
