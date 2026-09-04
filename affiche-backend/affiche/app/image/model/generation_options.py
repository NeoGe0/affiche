from dataclasses import dataclass, asdict, fields as dataclass_fields
import json

@dataclass
class GenerationOptions:

    jpeg_quality: int = 90

    def __post_init__(self):
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError(f"jpeg_quality must be between 1 and 100, got {self.jpeg_quality}")

    @classmethod
    def from_dict(cls, data: dict) -> "GenerationOptions":
        fields = {f.name for f in dataclass_fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in fields})

    def model_dump(self) -> dict:
        return asdict(self)

    def model_dump_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def model_validate_json(cls, json_str: str) -> "GenerationOptions":
        return cls(**json.loads(json_str))
