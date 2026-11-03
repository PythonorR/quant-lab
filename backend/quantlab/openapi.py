"""Print the OpenAPI schema (used to generate the frontend's TypeScript types)."""
import json

from quantlab.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=1))
