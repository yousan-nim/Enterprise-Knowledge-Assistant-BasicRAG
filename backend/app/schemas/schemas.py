from pydantic import BaseModel, ConfigDict, Field, model_validator



class GroundedAnswer(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    answer: str = Field(min_length=1, description="Answer the question using only the excerpts, in the question language.")
    citation_ids: list[str] = Field(description="Exact IDs of excerpts supporting the answer; empty when no answer is found.")
    found: bool = Field(description="True when the excerpts contain the information requested by the question.")

    @model_validator(mode="after")
    def check_consistency(self):
        if self.found:
            if not self.citation_ids:
                raise ValueError("An answer must include citations.")
        else:
            if self.citation_ids:
                raise ValueError("An abstention must not include citations.")

            if self.answer != "ไม่พบข้อมูลในเอกสาร":
                raise ValueError("An abstention must use the expected message.")

        return self


class AnswerDraft(BaseModel):
    """Model output before the application adds the public found status."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        str_strip_whitespace=True,
    )

    question_in_english: str = Field(default="", description="Translate the user question into English before reading the evidence.")
    answer: str
    citation_ids: list[str]

    @model_validator(mode="after")
    def check_evidence(self):
        if self.answer == "ไม่พบข้อมูลในเอกสาร":
            raise ValueError("Use an empty answer and empty citations when evidence is absent.")
        if bool(self.answer) != bool(self.citation_ids):
            raise ValueError("Provide both an answer and citations, or leave both empty.")
        return self
