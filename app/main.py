from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yaml
from jinja2 import Environment, FileSystemLoader
import traceback
import logging

# ensure logs directory exists
import os as _os
_os.makedirs("logs", exist_ok=True)

# configure basic file logging for server exceptions
logging.basicConfig(filename="logs/server.log", level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# IMPORTANT: adjust import based on your repo
from transformer.core import transform_spec
from utils.file_loader import save_yaml
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")
# Jinja2 environment used for simple rendering without TemplateResponse
jinja_env = Environment(loader=FileSystemLoader("templates"))


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler that logs tracebacks to a file for easier debugging."""
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logging.error("Unhandled exception during request %s %s:\n%s", request.method, request.url, tb)
    # also save the last traceback in an easy-to-find place
    try:
        with open("logs/last_error.txt", "w", encoding="utf-8") as f:
            f.write(tb)
    except Exception:
        pass

    # Return a friendly error page (avoid exposing internals)
    try:
        template = jinja_env.get_template("index.html")
        content = template.render(request=None, error="Internal Server Error (details logged).")
        return HTMLResponse(content, status_code=500)
    except Exception:
        return HTMLResponse("Internal Server Error", status_code=500)


@app.get("/health")
def health():
    """Simple health endpoint used for readiness/liveness checks."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Render the UI template without using TemplateResponse to avoid
    TemplateResponse's global caching edge-cases that can raise
    'unhashable type' errors in some environments.
    """
    try:
        template = jinja_env.get_template("index.html")
        content = template.render()
        return HTMLResponse(content)
    except Exception as e:
        # Fall back to a minimal HTML response with the form if rendering fails
        fallback = """
        <html><body><h2>Swagger → AWS Converter</h2>
        <form action='/transform' method='post' enctype='multipart/form-data'>
        <input type='file' name='file' required>
        <button type='submit' name='action' value='transform'>Transform</button>
        <button type='submit' name='action' value='run'>Run (save output)</button>
        </form></body></html>
        """
        return HTMLResponse(fallback, status_code=200)


@app.post("/transform", response_class=HTMLResponse)
async def transform(request: Request):
    """
    Transform endpoint.

    Note: to avoid requiring the optional `python-multipart` package at import time,
    we don't declare UploadFile/File in the signature. If multipart parsing is not
    available at runtime, the endpoint will attempt to read the raw body as a
    fallback.
    """
    content = None

    # Try to read multipart/form-data (requires python-multipart at runtime)
    try:
        form = await request.form()
        file_field = form.get("file")
        if file_field is not None:
            # Starlette UploadFile exposes .read
            if hasattr(file_field, "read"):
                content = await file_field.read()
            else:
                # Could be a raw string/bytes
                content = file_field if isinstance(file_field, (bytes, str)) else None
    except Exception:
        # multipart parser not available or other error; fall back to raw body
        content = None

    if content is None:
        # fallback: read entire request body (works if caller sent application/yaml or text)
        try:
            content = await request.body()
        except Exception as e:
            template = jinja_env.get_template("index.html")
            content = template.render(request=None, error=f"could not read request body: {e}")
            return HTMLResponse(content)

    try:
        # parse the uploaded/raw YAML
        spec = yaml.safe_load(content)
        transformed = transform_spec(spec)

        output_yaml = yaml.dump(transformed, sort_keys=False)

        # determine action from form (transform vs run)
        action = None
        try:
            form = await request.form()
            action = form.get("action")
        except Exception:
            action = None

        if action == "run":
            # centralize the run logic by using run.run_transform
            try:
                from run import run_transform

                result = run_transform(spec=spec, output_path=os.path.join("specs", "output", "run_output.yaml"), deploy=False)
                out_path = result["output_path"]
                template = jinja_env.get_template("index.html")
                content = template.render(request=None, output=output_yaml, message=f"Saved transformed spec to {out_path}")
                return HTMLResponse(content)
            except Exception as e:
                template = jinja_env.get_template("index.html")
                content = template.render(request=None, error=f"run failed: {e}")
                return HTMLResponse(content)

        template = jinja_env.get_template("index.html")
        content = template.render(request=None, output=output_yaml)
        return HTMLResponse(content)

    except Exception as e:
        template = jinja_env.get_template("index.html")
        content = template.render(request=None, error=str(e))
        return HTMLResponse(content)
