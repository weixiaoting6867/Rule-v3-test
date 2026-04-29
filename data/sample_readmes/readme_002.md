# Requests: HTTP for Humans

Requests is an elegant and simple HTTP library for Python. It is built with urllib3 and
depends on certifi for SSL certificate verification.

## Supported Versions

Requests supports Python 3.7+. It also supports PyPy.

## Usage

```python
import requests
r = requests.get('https://api.github.com/events')
```

Requests provides connection pooling, multipart file uploads, and automatic content decoding.
Requests integrates with OAuth for authentication workflows.
