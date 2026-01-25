import re

class DataValidator:
    def __init__(self):
        pass

    def validate(self, data: dict) -> dict:
        """
        Validates the extracted data and returns a list of warnings/errors.
        Also adds a 'validation_status' field.
        """
        errors = []
        warnings = []

        # Validate Date
        if not data.get("date"):
            errors.append("Missing Date")

        # Validate Total
        if data.get("total") is None:
            errors.append("Missing Total Amount")

        # Validate GSTIN format (if present)
        gstin = data.get("gstin")
        if gstin:
             if not re.match(r"\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}", gstin):
                 warnings.append("Invalid GSTIN Format")
        
        # Add validation metadata
        data["validation_errors"] = errors
        data["validation_warnings"] = warnings
        data["is_valid"] = len(errors) == 0

        return data
