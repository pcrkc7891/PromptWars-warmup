"""
Custom exception models for the Triage application.
"""

class TriageAPIError(Exception):
    """Custom exception for API errors with an associated HTTP status code."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class VertexGenerationError(TriageAPIError):
    """Specific exception for Vertex AI generation failures."""
