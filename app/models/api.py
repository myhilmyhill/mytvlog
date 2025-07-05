from typing import Annotated, Literal
from fastapi import Query
from pydantic import AfterValidator, BaseModel, Field, computed_field
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import json

JST = ZoneInfo("Asia/Tokyo")

def localize_to_jst(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=JST)
    return dt.astimezone(JST)

JSTDatetime = Annotated[datetime, AfterValidator(localize_to_jst)]

class ProgramQueryParams(BaseModel):
    page: int = Query(default=1)
    size: int = Query(default=100)
    from_: JSTDatetime | None | Literal[""] = Query(default=None)
    to: JSTDatetime | None | Literal[""] = Query(default=None)
    name: str = Query(default="")

class ProgramBase(BaseModel):
    event_id: int
    service_id: int
    name: str
    start_time: datetime
    duration: int
    text: str | None = None
    ext_text: str | None = None
    created_at: datetime | None = None

class ProgramGetBase(ProgramBase):
    id: int | str
    created_at: datetime

    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.duration)

class ProgramGet(ProgramGetBase):
    viewed_times_json: str | None = Field(exclude=True)

    @computed_field
    @property
    def viewed_times(self) -> list[datetime]:
        times = json.loads(self.viewed_times_json or '[]')
        result = []
        for t in times:
            if isinstance(t, int):
                dt = datetime.fromtimestamp(t).astimezone(JST)
            elif isinstance(t, str):
                dt = datetime.fromisoformat(t).astimezone(JST)
            else:
                continue
            result.append(dt)
        return result

class ViewQueryParams(BaseModel):
    program_id: int | str | None = Query(default=None)
    page: int | None = Query(default=1, gt=0, title="program_id 指定時は無視されて全件取得します")
    size: int | None = Query(default=500, gt=0, title="program_id 指定時は無視されて全件取得します")

class ViewBase(BaseModel):
    viewed_time: datetime
    created_at: datetime

class ViewGet(ViewBase):
    program_id: int | str

class ViewPost(ViewBase):
    program: ProgramBase
    created_at: datetime = datetime.now()

class RecordingQueryParams(BaseModel):
    program_id: int | str | None = Query(default=None)
    # TODO: バグでaliasが効かない
    from_: JSTDatetime | None | Literal[""] = Query(default=None, alias="from")
    to: JSTDatetime | None | Literal[""] = Query(default=None)
    watched: bool | Literal["on"] = Query(default=False)
    deleted: bool | Literal["on"] = Query(default=False)
    file_folder: str = Query(default="")

class RecordingBase(BaseModel):
    program: ProgramBase
    file_path: str
    file_size: int | None
    watched_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime

class RecordingGet(RecordingBase):
    program: ProgramGetBase
    id: int | str

    @computed_field
    @property
    def file_folder(self) -> str | None:
        s = self.file_path.split("/")
        return s[3] if len(s) > 3 else None

class RecordingPost(RecordingBase):
    file_folder: str | None = None
    file_size: int | None = None
    watched_at: datetime | None = None
    deleted_at: datetime | None = None
    created_at: datetime = datetime.now()

class RecordingPatch(BaseModel):
    file_path: str | None = Field(
        default=None,
        title="変更しても、実際のファイルの場所は移動されません。file_folder, deleted_at と同時に設定できません",
    )
    file_folder: str | None = Field(
        default=None, title="変更した場合、実際のファイルの場所も移動されます"
    )
    watched_at: datetime | None = None
    deleted_at: datetime | None = Field(
        default=None, title="値を設定した場合、実際のファイルも削除されます"
    )

class Digestion(BaseModel):
    id: int | str
    name: str
    service_id: int
    start_time: datetime
    duration: int
    viewed_times_json: str | None = Field(exclude=True)

    @computed_field
    @property
    def end_time(self) -> datetime:
        return self.start_time + timedelta(seconds=self.duration)

    @computed_field
    @property
    def viewed_times(self) -> list[datetime]:
        times = json.loads(self.viewed_times_json or '[]')
        result = []
        for t in times:
            if isinstance(t, int):
                dt = datetime.fromtimestamp(t).astimezone(JST)
            elif isinstance(t, str):
                dt = datetime.fromisoformat(t).astimezone(JST)
            else:
                continue
            result.append(dt)
        return result
