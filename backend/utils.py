from pydantic import BaseModel

class TextRequest(BaseModel):
    text : str
    source_nllb_code: str
    ocr_lang_code: str

class SidebarData(BaseModel):
    device: bool