import re
from enum import Enum, auto
from typing import Optional


class _ParaState(Enum):
    SEARCHING = auto()
    OUTSIDE_STRING = auto()
    IN_STRING = auto()
    ESCAPE = auto()


class StreamExtractor:
    """Incrementally extract title and paragraph content from accumulating LLM JSON output.

    Call feed(buffer) on every token append. It returns a list of events to yield.
    The extractor only processes new characters since the last call.
    """

    _TITLE_RE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"')

    def __init__(self):
        self._yielded_title: bool = False
        self._cursor: int = 0
        self._para_state: _ParaState = _ParaState.SEARCHING
        self._para_array_start: int = -1
        self._current_para_index: int = 0
        self._pending_chars: list[str] = []
        self._flush_threshold: int = 1

    def feed(self, buffer: str) -> list[dict]:
        events = []

        if not self._yielded_title:
            title = self._try_extract_title(buffer)
            if title is not None:
                events.append({"type": "stream_title", "title": title})
                self._yielded_title = True

        new_events = self._process_paragraphs(buffer)
        events.extend(new_events)
        return events

    def _try_extract_title(self, text: str) -> Optional[str]:
        clean = self._strip_preamble(text)
        m = self._TITLE_RE.search(clean)
        if m:
            return self._unescape(m.group(1))
        return None

    def _process_paragraphs(self, buffer: str) -> list[dict]:
        events = []

        if self._para_state == _ParaState.SEARCHING:
            idx = buffer.find('"paragraphs"', self._cursor)
            if idx < 0:
                self._cursor = max(0, len(buffer) - 20)
                return events
            bracket = buffer.find('[', idx)
            if bracket < 0:
                self._cursor = idx
                return events
            self._para_array_start = bracket + 1
            self._para_state = _ParaState.OUTSIDE_STRING
            self._cursor = self._para_array_start

        while self._cursor < len(buffer):
            ch = buffer[self._cursor]

            if self._para_state == _ParaState.OUTSIDE_STRING:
                if ch == '"':
                    self._para_state = _ParaState.IN_STRING
                    self._cursor += 1
                    continue
                elif ch == ']':
                    if self._pending_chars:
                        events.append({
                            "type": "stream_token",
                            "paragraph_index": self._current_para_index,
                            "content": "".join(self._pending_chars),
                        })
                        self._pending_chars = []
                    self._para_state = _ParaState.SEARCHING
                    self._cursor += 1
                    break
                else:
                    self._cursor += 1
                    continue

            elif self._para_state == _ParaState.IN_STRING:
                if ch == '\\':
                    self._para_state = _ParaState.ESCAPE
                    self._cursor += 1
                    continue
                elif ch == '"':
                    if self._pending_chars:
                        events.append({
                            "type": "stream_token",
                            "paragraph_index": self._current_para_index,
                            "content": "".join(self._pending_chars),
                        })
                        self._pending_chars = []
                    self._current_para_index += 1
                    self._para_state = _ParaState.OUTSIDE_STRING
                    self._cursor += 1
                    continue
                else:
                    self._pending_chars.append(ch)
                    if len(self._pending_chars) >= self._flush_threshold:
                        events.append({
                            "type": "stream_token",
                            "paragraph_index": self._current_para_index,
                            "content": "".join(self._pending_chars),
                        })
                        self._pending_chars = []
                    self._cursor += 1
                    continue

            elif self._para_state == _ParaState.ESCAPE:
                escaped = self._resolve_escape(ch)
                self._pending_chars.append(escaped)
                if len(self._pending_chars) >= self._flush_threshold:
                    events.append({
                        "type": "stream_token",
                        "paragraph_index": self._current_para_index,
                        "content": "".join(self._pending_chars),
                    })
                    self._pending_chars = []
                self._para_state = _ParaState.IN_STRING
                self._cursor += 1
                continue

        return events

    @staticmethod
    def _strip_preamble(text: str) -> str:
        idx = text.find('{')
        return text[idx:] if idx >= 0 else text

    @staticmethod
    def _unescape(s: str) -> str:
        return (s
                .replace('\\"', '"')
                .replace('\\n', '\n')
                .replace('\\t', '\t')
                .replace('\\\\', '\\'))

    @staticmethod
    def _resolve_escape(ch: str) -> str:
        if ch == 'n':
            return '\n'
        if ch == 't':
            return '\t'
        if ch == '"':
            return '"'
        if ch == '\\':
            return '\\'
        if ch == '/':
            return '/'
        return ch


class MetaIntroStreamExtractor:
    """Handles the compound meta+intro JSON structure.

    Yields stream_meta once meta.title and meta.description are found,
    then delegates to StreamExtractor scoped at the intro sub-object.
    """

    _META_TITLE_RE = re.compile(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"')
    _META_DESC_RE = re.compile(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"')
    _INTRO_RE = re.compile(r'"intro"\s*:\s*\{')

    def __init__(self):
        self._yielded_meta: bool = False
        self._intro_extractor: Optional[StreamExtractor] = None
        self._intro_offset: int = -1
        self._meta_section_end: int = -1

    def feed(self, buffer: str) -> list[dict]:
        events = []
        working = self._strip_preamble(buffer)

        if not self._yielded_meta:
            meta = self._try_extract_meta(working)
            if meta:
                events.append({"type": "stream_meta", "meta": meta})
                self._yielded_meta = True

        if self._intro_offset < 0:
            m = self._INTRO_RE.search(working)
            if m:
                self._intro_offset = m.start()
                self._intro_extractor = StreamExtractor()

        if self._intro_extractor and self._intro_offset >= 0:
            intro_text = working[self._intro_offset:]
            intro_events = self._intro_extractor.feed(intro_text)
            events.extend(intro_events)

        return events

    def _try_extract_meta(self, text: str) -> Optional[dict]:
        meta_start = text.find('"meta"')
        if meta_start < 0:
            return None
        intro_start = text.find('"intro"')
        if intro_start < 0:
            meta_section = text[meta_start:]
        else:
            meta_section = text[meta_start:intro_start]
            self._meta_section_end = intro_start

        title_m = self._META_TITLE_RE.search(meta_section)
        desc_m = self._META_DESC_RE.search(meta_section)
        if title_m and desc_m:
            return {
                "title": StreamExtractor._unescape(title_m.group(1)),
                "description": StreamExtractor._unescape(desc_m.group(1)),
            }
        return None

    @staticmethod
    def _strip_preamble(text: str) -> str:
        idx = text.find('{')
        return text[idx:] if idx >= 0 else text
