class ESDocsException(Exception):
    pass


class InvalidFieldLookup(ESDocsException):
    pass


class MissingSerializer(ESDocsException):
    pass
