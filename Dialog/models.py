from pydantic import BaseModel

class Session(BaseModel):
    """
    Represents a user session.
    """
    session_id: int
    session_name: str

class Dialog(BaseModel):
    """
    Represents a dialog entry.
    """
    dialog_id: int
    question: str
    dialog_content: str

class Result(BaseModel):
    """
    Represents the result of a dialog operation.
    """
    type: int
    message: str
    session_history: list[Session] = []
    dialog_history: list[Dialog] = []

class Task(BaseModel):
    """
    Represents the body of a question request.
    """
    task_id: str
    user_id: int
    session_id: int
    question: str