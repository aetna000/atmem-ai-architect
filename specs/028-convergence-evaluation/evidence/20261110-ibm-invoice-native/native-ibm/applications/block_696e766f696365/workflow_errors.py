"""Sanitized failure categories; never carry raw model/document/provider text."""
class TemporaryWork(Exception):pass
class PermanentWork(Exception):pass
class ExternalOutcomeUnknown(Exception):pass
class DestinationNotAttempted(TemporaryWork):pass
class InvalidDispatch(PermanentWork):pass
