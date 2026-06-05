"""In-memory patient record store for development and testing."""

from dataclasses import dataclass, field


@dataclass
class PatientRecord:
    patient_id: str
    name: str
    date_of_birth: str
    conditions: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    clinical_notes: str = ""


class PatientRecordStore:
    """Simple store — replace with EHR integration in production."""

    def __init__(self):
        self._records: dict[str, PatientRecord] = {}

    def add(self, record: PatientRecord) -> None:
        self._records[record.patient_id] = record

    def get(self, patient_id: str) -> PatientRecord | None:
        return self._records.get(patient_id)

    def list_ids(self) -> list[str]:
        return list(self._records.keys())
