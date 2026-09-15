class KnowledgeNotFoundError(Exception):
    pass


class KnowledgeAccessDeniedError(Exception):
    pass


class LibraryNotFoundError(Exception):
    pass


class ExtractionError(Exception):
    pass


class EmptyTextLayerError(ExtractionError):
    pass


class UnsupportedSourceError(ExtractionError):
    pass
