from abc import ABC, abstractmethod
from datetime import datetime
from ..models.api import ProgramBase, ProgramQueryParams, ProgramGet, ViewBase, ViewQueryParams, ViewGet, RecordingBase, RecordingQueryParams, RecordingGet, Series, SeriesWithPrograms, SeriesQueryParams, Digestion

class ProgramRepository(ABC):
    @abstractmethod
    def search(self, params: ProgramQueryParams) -> list[ProgramGet]: ...

    @abstractmethod
    def get_by_id(self, id: int | str) -> ProgramGet: ...

    @abstractmethod
    def get_or_create(self, program: ProgramBase, created_at: datetime, viewed_time: datetime) -> int | str: ...

class ViewRepository(ABC):
    @abstractmethod
    def search(self, params: ViewQueryParams) -> list[ViewGet]: ...

    @abstractmethod
    def create(self, program_id: int | str, view: ViewBase) -> None: ...

class RecordingRepository(ABC):
    @abstractmethod
    def search(self, params: RecordingQueryParams) -> list[RecordingGet]: ...

    @abstractmethod
    def get_by_id(self, id: int | str) -> RecordingGet: ...

    @abstractmethod
    def create(self, recording: RecordingBase, program_id: int | str) -> int | str: ...

    @abstractmethod
    def update_patch(self, id: int | str, patch: dict) -> bool: ...

class SeriesRepository(ABC):
    @abstractmethod
    def search(self, params: SeriesQueryParams) -> list[Series]: ...

    @abstractmethod
    def get_by_id(self, id: int | str) -> SeriesWithPrograms | None: ...

    @abstractmethod
    def create(self, title: str, created_at: datetime) -> int | str: ...

    @abstractmethod
    def add_program(self, series_id: int | str, program_id: int | str) -> None: ...

class DigestionRepository(ABC):
    @abstractmethod
    def list_digestions(self) -> list[Digestion]: ...
