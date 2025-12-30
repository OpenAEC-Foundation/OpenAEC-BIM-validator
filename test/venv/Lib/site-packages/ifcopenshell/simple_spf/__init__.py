try:
    from parser.parse import parse
    from parser.file import file, open
    from parser.errors import _ValidationError, CollectedValidationErrors, DuplicateNameError, HeaderFieldError
except:
    from .parser.parse import parse 
    from .parser.file import file, open 
    from .parser.errors import _ValidationError, CollectedValidationErrors, DuplicateNameError, HeaderFieldError

__all__ = ["parse", "open", "file", "_ValidationError", 
           "CollectedValidationErrors", "DuplicateNameError", "HeaderFieldError"] # for testing 