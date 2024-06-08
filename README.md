# Simple Webhook

## Usage

### Create a background task

```shell
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name": "<name>", "parameters": []}' \
  'http://localhost:8000/api/webhook'
```

### Wait for task to complete

```shell
bash wait.sh <name> <secret>
```