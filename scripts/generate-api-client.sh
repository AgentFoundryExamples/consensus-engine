#!/bin/bash
set -e

echo "Generating OpenAPI specification from backend..."

# Navigate to the project root
cd "$(dirname "$0")/.."

# Set minimal env vars to avoid validation errors during spec generation
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-key-for-openapi-generation}"
export ENV="${ENV:-development}"

# Generate OpenAPI spec from FastAPI app
python3 -c "
import json
import sys
from consensus_engine.app import app

spec = app.openapi()
print(json.dumps(spec, indent=2))
" > webapp/openapi.json

echo "OpenAPI spec saved to webapp/openapi.json"

# Navigate to webapp directory
cd webapp

echo "Generating TypeScript API client..."

# Generate TypeScript client from OpenAPI spec
npx openapi-typescript-codegen \
  --input openapi.json \
  --output src/api/generated \
  --client axios

echo "TypeScript API client generated successfully in src/api/generated/"
echo ""
echo "To use the client in your code:"
echo "  import { DefaultService } from './api/generated';"
