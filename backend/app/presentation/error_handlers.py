from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.dataset.errors import DatasetNotFoundError, DomainError, FileTooLargeError


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DatasetNotFoundError)
    async def dataset_not_found(_: Request, error: DatasetNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": error.message})

    @app.exception_handler(FileTooLargeError)
    async def file_too_large(_: Request, error: FileTooLargeError) -> JSONResponse:
        return JSONResponse(status_code=413, content={"detail": error.message})

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": error.message})
