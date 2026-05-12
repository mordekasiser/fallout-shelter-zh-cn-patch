from __future__ import annotations

from dataclasses import dataclass


PPtr = tuple[int, int]


class ParseError(ValueError):
    pass


@dataclass(frozen=True)
class LanguageData:
    name: str
    code: str


@dataclass(frozen=True)
class TermData:
    term: str
    term_type: int
    description: str
    languages: list[str]
    languages_touch: list[str]
    flags: list[int]


@dataclass(frozen=True)
class LanguageSourceData:
    game_object: PPtr
    enabled: bool
    script: PPtr
    name: str
    google_web_service_url: str
    google_spreadsheet_key: str
    google_spreadsheet_name: str
    google_last_updated_version: str
    google_update_frequency: int
    terms: list[TermData]
    languages: list[LanguageData]
    case_insensitive_terms: bool
    assets: list[PPtr]
    never_destroy: bool
    user_agrees_to_have_it_on_the_scene: bool
    trailing_data: bytes = b""


class UnityBinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def remaining(self) -> int:
        return len(self.data) - self.offset

    def read(self, size: int) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise ParseError(f"read out of bounds at {self.offset} for {size} bytes")
        value = self.data[self.offset : self.offset + size]
        self.offset += size
        return value

    def align4(self) -> None:
        padding = (-self.offset) % 4
        if padding:
            self.read(padding)

    def read_u8(self) -> int:
        return self.read(1)[0]

    def read_i32(self) -> int:
        return int.from_bytes(self.read(4), "little", signed=True)

    def read_i64(self) -> int:
        return int.from_bytes(self.read(8), "little", signed=True)

    def read_bool(self) -> bool:
        value = self.read_u8() != 0
        self.align4()
        return value

    def read_aligned_string(self) -> str:
        size = self.read_i32()
        if size < 0:
            raise ParseError(f"negative string length at {self.offset - 4}: {size}")
        value = self.read(size).decode("utf-8", errors="replace")
        self.align4()
        return value

    def read_string_array(self) -> list[str]:
        size = self.read_i32()
        if size < 0:
            raise ParseError(f"negative string array length at {self.offset - 4}: {size}")
        return [self.read_aligned_string() for _ in range(size)]

    def read_int_array(self) -> list[int]:
        size = self.read_i32()
        if size < 0:
            raise ParseError(f"negative int array length at {self.offset - 4}: {size}")
        return [self.read_i32() for _ in range(size)]

    def read_pptr(self) -> tuple[int, int]:
        file_id = self.read_i32()
        path_id = self.read_i64()
        return file_id, path_id


class UnityBinaryWriter:
    def __init__(self):
        self.parts: list[bytes] = []
        self.offset = 0

    def write(self, value: bytes) -> None:
        self.parts.append(value)
        self.offset += len(value)

    def align4(self) -> None:
        padding = (-self.offset) % 4
        if padding:
            self.write(b"\x00" * padding)

    def write_u8(self, value: int) -> None:
        if not 0 <= value <= 0xFF:
            raise ValueError(f"u8 out of range: {value}")
        self.write(bytes([value]))

    def write_i32(self, value: int) -> None:
        self.write(int(value).to_bytes(4, "little", signed=True))

    def write_i64(self, value: int) -> None:
        self.write(int(value).to_bytes(8, "little", signed=True))

    def write_bool(self, value: bool) -> None:
        self.write_u8(1 if value else 0)
        self.align4()

    def write_aligned_string(self, value: str) -> None:
        raw = value.encode("utf-8")
        self.write_i32(len(raw))
        self.write(raw)
        self.align4()

    def write_string_array(self, values: list[str]) -> None:
        self.write_i32(len(values))
        for value in values:
            self.write_aligned_string(value)

    def write_int_array(self, values: list[int]) -> None:
        self.write_i32(len(values))
        for value in values:
            self.write_i32(value)

    def write_pptr(self, value: PPtr) -> None:
        file_id, path_id = value
        self.write_i32(file_id)
        self.write_i64(path_id)

    def to_bytes(self) -> bytes:
        return b"".join(self.parts)


def read_term(reader: UnityBinaryReader) -> TermData:
    return TermData(
        term=reader.read_aligned_string(),
        term_type=reader.read_i32(),
        description=reader.read_aligned_string(),
        languages=reader.read_string_array(),
        languages_touch=reader.read_string_array(),
        flags=reader.read_int_array(),
    )


def read_language(reader: UnityBinaryReader) -> LanguageData:
    return LanguageData(
        name=reader.read_aligned_string(),
        code=reader.read_aligned_string(),
    )


def write_term(writer: UnityBinaryWriter, term: TermData) -> None:
    writer.write_aligned_string(term.term)
    writer.write_i32(term.term_type)
    writer.write_aligned_string(term.description)
    writer.write_string_array(term.languages)
    writer.write_string_array(term.languages_touch)
    writer.write_int_array(term.flags)


def write_language(writer: UnityBinaryWriter, language: LanguageData) -> None:
    writer.write_aligned_string(language.name)
    writer.write_aligned_string(language.code)


def parse_language_source(raw: bytes) -> LanguageSourceData:
    reader = UnityBinaryReader(raw)

    game_object = reader.read_pptr()
    enabled = reader.read_bool()
    script = reader.read_pptr()
    name = reader.read_aligned_string()
    google_web_service_url = reader.read_aligned_string()
    google_spreadsheet_key = reader.read_aligned_string()
    google_spreadsheet_name = reader.read_aligned_string()
    google_last_updated_version = reader.read_aligned_string()
    google_update_frequency = reader.read_i32()

    term_count = reader.read_i32()
    if term_count < 0:
        raise ParseError(f"negative term count: {term_count}")
    terms = [read_term(reader) for _ in range(term_count)]

    language_count = reader.read_i32()
    if language_count < 0:
        raise ParseError(f"negative language count: {language_count}")
    languages = [read_language(reader) for _ in range(language_count)]

    case_insensitive_terms = reader.read_bool()

    asset_count = reader.read_i32()
    if asset_count < 0:
        raise ParseError(f"negative asset count: {asset_count}")
    assets = [reader.read_pptr() for _ in range(asset_count)]

    never_destroy = reader.read_bool()
    user_agrees = reader.read_bool()
    trailing_data = reader.read(reader.remaining())

    return LanguageSourceData(
        game_object=game_object,
        enabled=enabled,
        script=script,
        name=name,
        google_web_service_url=google_web_service_url,
        google_spreadsheet_key=google_spreadsheet_key,
        google_spreadsheet_name=google_spreadsheet_name,
        google_last_updated_version=google_last_updated_version,
        google_update_frequency=google_update_frequency,
        terms=terms,
        languages=languages,
        case_insensitive_terms=case_insensitive_terms,
        assets=assets,
        never_destroy=never_destroy,
        user_agrees_to_have_it_on_the_scene=user_agrees,
        trailing_data=trailing_data,
    )


def serialize_language_source(source: LanguageSourceData) -> bytes:
    writer = UnityBinaryWriter()
    writer.write_pptr(source.game_object)
    writer.write_bool(source.enabled)
    writer.write_pptr(source.script)
    writer.write_aligned_string(source.name)
    writer.write_aligned_string(source.google_web_service_url)
    writer.write_aligned_string(source.google_spreadsheet_key)
    writer.write_aligned_string(source.google_spreadsheet_name)
    writer.write_aligned_string(source.google_last_updated_version)
    writer.write_i32(source.google_update_frequency)

    writer.write_i32(len(source.terms))
    for term in source.terms:
        write_term(writer, term)

    writer.write_i32(len(source.languages))
    for language in source.languages:
        write_language(writer, language)

    writer.write_bool(source.case_insensitive_terms)
    writer.write_i32(len(source.assets))
    for asset in source.assets:
        writer.write_pptr(asset)

    writer.write_bool(source.never_destroy)
    writer.write_bool(source.user_agrees_to_have_it_on_the_scene)
    writer.write(source.trailing_data)
    return writer.to_bytes()
