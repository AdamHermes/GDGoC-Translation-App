from pydantic import BaseModel

class TextRequest(BaseModel):
    text : str

class SidebarData(BaseModel):
    device: bool