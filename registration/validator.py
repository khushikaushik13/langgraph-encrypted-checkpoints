from typing import Dict, List, Literal, Optional, Set
from registration.state import RegistrationState


class RegistrationValidator:
    def __init__(self, required_fields: Optional[Set[str]] = None):
        self.required_fields = required_fields or {"name", "email", "pan"}

    def validate_present_fields(self, state: RegistrationState) -> RegistrationState:
        errors: Dict[str, str] = {}

        if state.name is not None:
            if len(state.name.strip()) < 2:
                errors["name"] = "Name must be atleast 2 characters"

        if state.phone is not None:
            p = state.phone.strip()
            if not (p.isdigit() and len(p) == 10):
                errors["phone"] = "Phone must be exactly 10 digits."

        if state.dob is not None:
            parts = state.dob.split("-")
            if not (len(parts) == 3 and all(part.isdigit() for part in parts)):
                errors["dob"] = "DOB must be in DD-MM-YYYY format."

        if state.pan is not None:
            pan = state.pan.strip().upper()
            if len(pan) != 10:
                errors["pan"] = "PAN must be 10 characters."

        return state.model_copy(update={"validation_errors": errors})

    def compute_missing_fields(self, state: RegistrationState) -> RegistrationState:
        missing: List[str] = []

        for field in self.required_fields:
            val = getattr(state, field, None)
            if val is None:
                missing.append(field)
                continue
            if isinstance(val, str) and val.strip() == "":
                missing.append(field)
                continue

        for field in state.validation_errors.keys():
            if field not in missing:
                missing.append(field)

        return state.model_copy(update={"missing_fields": sorted(missing)})

    @staticmethod
    def should_complete(state: RegistrationState) -> Literal["end", "complete"]:
        return "complete" if len(state.missing_fields) == 0 else "end"