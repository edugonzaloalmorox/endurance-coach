"""Provider-neutral daily wellness observations."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WellnessObservation(BaseModel):
    """One dated set of measured recovery signals from an external source."""

    model_config = ConfigDict(extra="forbid")

    date: date
    source: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    resting_heart_rate_bpm: float | None = Field(default=None, ge=20, le=250)
    hrv_ms: float | None = Field(default=None, ge=0, le=1_000)
    sleep_seconds: int | None = Field(default=None, ge=0, le=172_800)

    @model_validator(mode="after")
    def contains_at_least_one_signal(self) -> "WellnessObservation":
        """Reject empty rows that would manufacture unavailable observations."""
        if all(
            value is None
            for value in (
                self.resting_heart_rate_bpm,
                self.hrv_ms,
                self.sleep_seconds,
            )
        ):
            raise ValueError("wellness observation requires at least one measured signal")
        return self
