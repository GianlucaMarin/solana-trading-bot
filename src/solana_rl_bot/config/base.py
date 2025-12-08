"""
Base configuration classes using Pydantic v2.
"""

from typing import Any, Dict
from pydantic import BaseModel, ConfigDict


class BaseConfig(BaseModel):
    """Base configuration class with Pydantic v2 settings."""

    model_config = ConfigDict(
        # Allow extra fields for forward compatibility
        extra="forbid",
        # Validate on assignment
        validate_assignment=True,
        # Use enum values instead of enum objects
        use_enum_values=True,
        # Populate by field name
        populate_by_name=True,
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_json(self) -> str:
        """Convert config to JSON string."""
        return self.model_dump_json(exclude_none=True, indent=2)
