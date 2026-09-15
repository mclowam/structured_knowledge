from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.users import api_v1_router
from app.services.errors import InvalidRefreshTokenError

app = FastAPI()

app.include_router(api_v1_router)


@app.exception_handler(InvalidRefreshTokenError)
async def invalid_refresh_token_handler(
        _: Request,
        __: InvalidRefreshTokenError,
) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": "invalid refresh token"})

@app.get("/health")
def health():
    return {"status": "OK"}


