from typing import Literal 
from pydantic import BaseModel, Field 


class DocumentPage(BaseModel): 
    page: int = Field(ge=1) 
    text: str 
    extraction_method: Literal["direct", "ocr"] = "direct"
    
    