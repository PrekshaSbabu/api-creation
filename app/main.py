from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import yaml

# IMPORTANT: adjust import based on your repo
from transformer.core import transform_spec

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/transform", response_class=HTMLResponse)
async def transform(request: Request, file: UploadFile = File(...)):
    content = await file.read()

    try:
        spec = yaml.safe_load(content)
        transformed = transform_spec(spec)

        output_yaml = yaml.dump(transformed, sort_keys=False)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "output": output_yaml
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": str(e)
            }
        )
