from abc import ABC, abstractmethod
from datetime import datetime
from ..models.api import ProgramBase, ProgramQueryParams, ProgramGet, ViewBase, ViewQueryParams, ViewGet, RecordingBase, RecordingQueryParams, RecordingGet, Digestion

class ProgramRepository(ABC):
    @abstractmethod
    def search(self, params: ProgramQueryParams) -> list[ProgramGet]: ...

    @abstractmethod
    def get_by_id(self, id: int) -> ProgramGet: ...

    @abstractmethod
    def get_or_create(self, program: ProgramBase, created_at: datetime, viewed_time: datetime) -> int: ...

class ViewRepository(ABC):
    @abstractmethod
    def search(self, params: ViewQueryParams) -> list[ViewGet]: ...

    @abstractmethod
    def create(self, program_id: int, view: ViewBase) -> None: ...

class RecordingRepository(ABC):
    @abstractmethod
    def search(self, params: RecordingQueryParams) -> list[RecordingGet]: ...

    @abstractmethod
    def get_by_id(self, id: int) -> RecordingGet: ...

    @abstractmethod
    def create(self, recording: RecordingBase, program_id: int) -> int: ...

    @abstractmethod
    def update_patch(self, id: int, patch: dict, smb, background_tasks, con_factory) -> bool: ...

class DigestionRepository(ABC):
    @abstractmethod
    def list_digestions(self) -> list[Digestion]: ...
