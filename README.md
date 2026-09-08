# golf-club-handicap-committee-docker

Golf Canada verification hub container with:

- Goose CLI agent (Ollama-backed)
- Golf Canada MCP bridge (`scripts/golf_canada_mcp.py`)
- Streamlit dashboard (`web_app.py`) on port `8501`

## Run

Build:

```bash
docker build -t golf-canada-verifier .
```

Start web dashboard:

```bash
docker run --rm -p 8501:8501 \
  -e GOLF_CANADA_TOKEN=your_token_here \
  -v "$(pwd)/reports:/workspace/reports" \
  golf-canada-verifier web
```
