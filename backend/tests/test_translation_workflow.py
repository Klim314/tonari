"""Workflow-level event sequence tests for TranslationWorkflow."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.models import Chapter, ChapterTranslation, TranslationSegment, Work
from services.exceptions import SegmentNotFoundError
from services.translation_stream import TranslationStreamService
from services.translation_workflow import (
    SegmentCompleteEvent,
    SegmentDeltaEvent,
    SegmentStartEvent,
    TranslationCompleteEvent,
    TranslationErrorEvent,
    TranslationStatusEvent,
    TranslationWorkflow,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_work(session) -> Work:
    work = Work(title="Test Work", source="test", source_id="test-work", source_meta={})
    session.add(work)
    session.flush()
    return work


def _make_chapter(session, work: Work, text: str = "彼は歩く。\n彼女も歩く。") -> Chapter:
    chapter = Chapter(
        work_id=work.id,
        idx=1,
        sort_key=Decimal(1),
        title="Chapter 1",
        normalized_text=text,
        text_hash="test-hash",
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


def _run(gen) -> list:
    """Collect all events from an async generator synchronously."""

    async def _inner():
        events = []
        async for event in gen:
            events.append(event)
        return events

    return asyncio.run(_inner())


def _run_until_cancelled(gen) -> tuple[list, bool]:
    """Collect events until CancelledError, returning (events, was_cancelled)."""

    async def _inner():
        events = []
        try:
            async for event in gen:
                events.append(event)
            return events, False
        except asyncio.CancelledError:
            return events, True

    return asyncio.run(_inner())


def _mock_agent(tokens: list[str] | None = None) -> MagicMock:
    """Return a mock TranslationAgent whose stream_segment yields the given tokens."""
    if tokens is None:
        tokens = ["hello", " world"]

    async def _stream(*args, **kwargs):
        for token in tokens:
            yield token

    agent = MagicMock()
    agent.context_window = 3
    agent.model = "test-model"
    agent.stream_segment = MagicMock(side_effect=_stream)
    return agent


# ---------------------------------------------------------------------------
# Tests — TranslationWorkflow._resolve_agent
# ---------------------------------------------------------------------------


class TestResolveAgent:
    def test_resolve_agent_uses_work_prompt(self, db_session):
        """Agent is constructed using the latest prompt version assigned to the work."""
        work = _make_work(db_session)
        db_session.commit()

        workflow = TranslationWorkflow(db_session)
        mock_prompt = MagicMock()
        mock_prompt.id = 1
        mock_version = MagicMock()
        mock_version.template = "custom template"
        mock_version.model = "custom-model"

        with (
            patch.object(
                workflow._prompt_service, "get_prompt_for_work", return_value=mock_prompt
            ),
            patch.object(
                workflow._prompt_service,
                "get_prompt_versions",
                return_value=([mock_version], 1, 1, 0),
            ),
            patch("services.translation_workflow.TranslationAgent") as mock_agent_cls,
        ):
            workflow._resolve_agent(work.id, prompt_override=None)
            call_kwargs = mock_agent_cls.call_args.kwargs
            assert call_kwargs["system_prompt"] == "custom template"
            assert call_kwargs["model"] == "custom-model"

    def test_resolve_agent_uses_override(self, db_session):
        """Prompt override takes precedence over the work's assigned prompt."""
        work = _make_work(db_session)
        db_session.commit()

        workflow = TranslationWorkflow(db_session)
        override = {"template": "override template", "model": "override-model"}

        with (
            patch.object(workflow._prompt_service, "get_prompt_for_work", return_value=None),
            patch("services.translation_workflow.TranslationAgent") as mock_agent_cls,
        ):
            workflow._resolve_agent(work.id, prompt_override=override)
            call_kwargs = mock_agent_cls.call_args.kwargs
            assert call_kwargs["system_prompt"] == "override template"
            assert call_kwargs["model"] == "override-model"

    def test_resolve_agent_falls_back_to_defaults(self, db_session):
        """No work prompt and no override → settings.translation_model is used."""
        work = _make_work(db_session)
        db_session.commit()

        workflow = TranslationWorkflow(db_session)

        with (
            patch.object(workflow._prompt_service, "get_prompt_for_work", return_value=None),
            patch("services.translation_workflow.TranslationAgent") as mock_agent_cls,
            patch("services.translation_workflow.settings") as mock_settings,
        ):
            mock_settings.translation_model = "default-model"
            mock_settings.translation_api_key = None
            mock_settings.translation_api_base_url = None
            mock_settings.translation_chunk_chars = 500
            mock_settings.translation_context_segments = 3
            workflow._resolve_agent(work.id, prompt_override=None)
            call_kwargs = mock_agent_cls.call_args.kwargs
            assert call_kwargs["model"] == "default-model"
            assert call_kwargs["system_prompt"] is None


# ---------------------------------------------------------------------------
# Tests — TranslationWorkflow.start_or_resume
# ---------------------------------------------------------------------------


class TestStartOrResume:
    def test_full_chapter(self, db_session):
        """Full event sequence for a fresh chapter translation."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "彼は歩く。\n\n彼女も歩く。")
        workflow = TranslationWorkflow(db_session)
        agent = _mock_agent(["translated text"])

        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events = _run(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        types = [type(e) for e in events]
        assert types[0] is TranslationStatusEvent
        assert events[0].status == "running"

        # "彼は歩く。" and "彼女も歩く。" are translatable; "\n\n" is whitespace
        translatable = [e for e in events if isinstance(e, SegmentStartEvent)]
        assert len(translatable) == 2

        for start_evt in translatable:
            idx = events.index(start_evt)
            assert isinstance(events[idx + 1], SegmentDeltaEvent)
            complete_events = [
                e
                for e in events[idx:]
                if isinstance(e, SegmentCompleteEvent) and e.segment_id == start_evt.segment_id
            ]
            assert complete_events, "Expected SegmentCompleteEvent for each segment"

        assert isinstance(events[-1], TranslationCompleteEvent)
        assert events[-1].status == "completed"

        translation = db_session.execute(
            select(ChapterTranslation).where(ChapterTranslation.chapter_id == chapter.id)
        ).scalar_one()
        assert translation.status == "completed"

        segments = db_session.execute(
            select(TranslationSegment).where(
                TranslationSegment.chapter_translation_id == translation.id,
                ~TranslationSegment.flags.contains(["whitespace"]),
            )
        ).scalars().all()
        for seg in segments:
            assert seg.tgt != ""

    def test_already_complete(self, db_session):
        """When no pending segments remain, only TranslationCompleteEvent is emitted."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "hello")
        workflow = TranslationWorkflow(db_session)

        svc = TranslationStreamService(db_session)
        translation = svc.get_or_create_translation(chapter.id)
        segments = svc.ensure_segments(translation, chapter.normalized_text)
        for seg in segments:
            if svc.needs_translation(seg):
                seg.tgt = "pre-translated"
                db_session.add(seg)
        db_session.commit()

        agent = _mock_agent()
        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events = _run(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        assert len(events) == 1
        assert isinstance(events[0], TranslationCompleteEvent)
        assert events[0].status == "completed"
        agent.stream_segment.assert_not_called()

    def test_skips_whitespace_segments(self, db_session):
        """Whitespace segments produce no SegmentStartEvent."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "line one\n\nline two")
        workflow = TranslationWorkflow(db_session)
        agent = _mock_agent(["ok"])

        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events = _run(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        start_events = [e for e in events if isinstance(e, SegmentStartEvent)]
        assert len(start_events) == 2
        for e in start_events:
            assert "\n\n" not in e.src

    def test_cancellation_sets_status_idle(self, db_session):
        """Disconnect during streaming sets status to idle; no TranslationCompleteEvent."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)
        agent = _mock_agent(["tok"])

        is_disconnected = AsyncMock(side_effect=[False, True])

        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events, was_cancelled = _run_until_cancelled(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=is_disconnected,
                )
            )

        assert was_cancelled
        assert not any(isinstance(e, TranslationCompleteEvent) for e in events)

        translation = db_session.execute(
            select(ChapterTranslation).where(ChapterTranslation.chapter_id == chapter.id)
        ).scalar_one()
        assert translation.status == "idle"

    def test_agent_error_emits_error_event(self, db_session):
        """Agent exception mid-stream yields TranslationErrorEvent; status set to error."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)

        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("agent exploded")
            yield  # make it an async generator

        agent = MagicMock()
        agent.context_window = 3
        agent.model = "test-model"
        agent.stream_segment = MagicMock(side_effect=_failing_stream)

        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events = _run(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        error_events = [e for e in events if isinstance(e, TranslationErrorEvent)]
        assert error_events
        assert "agent exploded" in error_events[0].error

        translation = db_session.execute(
            select(ChapterTranslation).where(ChapterTranslation.chapter_id == chapter.id)
        ).scalar_one()
        assert translation.status == "error"


# ---------------------------------------------------------------------------
# Tests — TranslationWorkflow.retranslate_segment
# ---------------------------------------------------------------------------


class TestRetranslateSegment:
    def test_retranslate_segment(self, db_session):
        """Single-segment retranslation: correct event sequence; translation status unchanged."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "line one\n\nline two")
        workflow = TranslationWorkflow(db_session)

        svc = TranslationStreamService(db_session)
        translation = svc.get_or_create_translation(chapter.id)
        segments = svc.ensure_segments(translation, chapter.normalized_text)
        first_segment = next(s for s in segments if svc.needs_translation(s))
        first_segment.tgt = "old translation"
        db_session.add(first_segment)
        translation.status = "completed"
        db_session.add(translation)
        db_session.commit()
        db_session.refresh(first_segment)

        agent = _mock_agent(["new translation"])
        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events = _run(
                workflow.retranslate_segment(
                    chapter,
                    first_segment.id,
                    work.id,
                    prompt_override=None,
                    instruction=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        types = [type(e) for e in events]
        assert SegmentStartEvent in types
        assert SegmentDeltaEvent in types
        assert SegmentCompleteEvent in types
        assert TranslationCompleteEvent in types
        assert TranslationStatusEvent not in types  # is_single_segment=True

        db_session.expire_all()
        updated_translation = db_session.execute(
            select(ChapterTranslation).where(ChapterTranslation.id == translation.id)
        ).scalar_one()
        assert updated_translation.status == "completed"  # unchanged by retranslation

        db_session.expire_all()
        updated_seg = db_session.execute(
            select(TranslationSegment).where(TranslationSegment.id == first_segment.id)
        ).scalar_one()
        assert updated_seg.tgt == "new translation"

    def test_retranslate_segment_with_instruction(self, db_session):
        """current_translation is captured from pre-reset tgt when instruction is given."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)

        svc = TranslationStreamService(db_session)
        translation = svc.get_or_create_translation(chapter.id)
        segments = svc.ensure_segments(translation, chapter.normalized_text)
        seg = next(s for s in segments if svc.needs_translation(s))
        seg.tgt = "original translation"
        db_session.add(seg)
        db_session.commit()
        db_session.refresh(seg)

        captured_current_translation = None

        async def _stream(
            src,
            *,
            preceding_segments=None,
            instruction=None,
            current_translation=None,
        ):
            nonlocal captured_current_translation
            captured_current_translation = current_translation
            yield "improved"

        agent = MagicMock()
        agent.context_window = 3
        agent.model = "test-model"
        agent.stream_segment = MagicMock(side_effect=_stream)

        with patch.object(workflow, "_resolve_agent", return_value=agent):
            _run(
                workflow.retranslate_segment(
                    chapter,
                    seg.id,
                    work.id,
                    prompt_override=None,
                    instruction="make it more casual",
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        assert captured_current_translation == "original translation"

    def test_retranslate_segment_not_found(self, db_session):
        """Missing segment raises SegmentNotFoundError."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "text")
        workflow = TranslationWorkflow(db_session)

        with pytest.raises(SegmentNotFoundError):
            _run(
                workflow.retranslate_segment(
                    chapter,
                    segment_id=99999,
                    work_id=work.id,
                    prompt_override=None,
                    instruction=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )
