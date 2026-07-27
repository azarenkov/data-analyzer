class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class DatasetNotFoundError(DomainError):
    def __init__(self, dataset_id: str) -> None:
        super().__init__(f"Dataset '{dataset_id}' not found")


class ColumnNotFoundError(DomainError):
    def __init__(self, column: str) -> None:
        super().__init__(f"Column '{column}' not found")


class UnsupportedFileError(DomainError):
    def __init__(self, filename: str) -> None:
        super().__init__(f"Unsupported file format: '{filename}'")


class FileParsingError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Failed to parse file: {reason}")


class InvalidQueryError(DomainError):
    pass


class FileTooLargeError(DomainError):
    def __init__(self, limit_bytes: int) -> None:
        super().__init__(f"File exceeds the upload limit of {limit_bytes // (1024 * 1024)} MB")


class EmptyDatasetError(DomainError):
    def __init__(self) -> None:
        super().__init__("Dataset contains no rows")
