import logging
import os
import uuid

import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.config import MAX_UPLOAD_BYTES, UPLOAD_DIR
from models.error import BusinessException
from models.response import ResponseModel
from routes.recipe import router as recipe_router
from routes.user import router as user_router
from utils.auth_token import TokenUtils

logger = logging.getLogger("recipe_app")

app = FastAPI(title="The Pantry API", version="1.0.0")

# Endpoints that do not need a login token
PUBLIC_PATHS = {"/auth/login", "/auth/signup", "/health", "/docs", "/redoc", "/openapi.json"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _error(code: int, message: str) -> JSONResponse:
    # The mobile client reads errors from the JSON body, so the HTTP status stays 200
    return JSONResponse(status_code=200, content={"code": code, "message": message, "data": None})


@app.exception_handler(BusinessException)
async def business_exception_handler(request: Request, exc: BusinessException):
    return _error(exc.status_code, exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = ", ".join(str(err["loc"][-1]) for err in exc.errors())
    return _error(1000, f"Invalid input: {fields}")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return _error(-2, "Internal server error")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return _error(1001, "Missing Authorization header")
    payload = TokenUtils.verify_token(auth_header[len("Bearer "):])
    if not payload:
        return _error(1001, "Token is invalid or expired")
    request.state.user = payload
    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(recipe_router, prefix="/recipe", tags=["recipe"])
app.include_router(user_router, prefix="/auth", tags=["user"])


@app.post("/upload", response_model=ResponseModel)
async def upload_file(file: UploadFile = File(...)):
    """Store a fridge photo and return its generated file name."""
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise BusinessException(1020)
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise BusinessException(1019)
    if not contents:
        raise BusinessException(1000, "Uploaded file is empty")
    unique_filename = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / unique_filename).write_bytes(contents)
    return ResponseModel.success_with_data(data={"filename": unique_filename})


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7777, reload=True)
