from pydantic import BaseModel

class TextRequest(BaseModel):
    text : str
    source_nllb_code: str

class SidebarData(BaseModel):
    device: bool