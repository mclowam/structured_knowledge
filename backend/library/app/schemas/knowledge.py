import enum


class SourceType(str, enum.Enum):
    file = "file"
    url = "url"


class LibraryStatus(str, enum.Enum):
    pending = "pending"
    extracting = "extracting"
    extracted = "extracted"
    compressing = "compressing"
    compressed = "compressed"
    quiz_ready = "quiz_ready"
    failed = "failed"