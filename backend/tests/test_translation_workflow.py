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
            patch.object(workflow._prompt_service, "get_prompt_for_work", return_value=mock_prompt),
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

        segments = (
            db_session.execute(
                select(TranslationSegment).where(
                    TranslationSegment.chapter_translation_id == translation.id,
                    ~TranslationSegment.flags.contains(["whitespace"]),
                )
            )
            .scalars()
            .all()
        )
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

    def test_cancellation_persists_partial_segment_text(self, db_session):
        """Disconnect after a delta keeps the partial text resumable on the segment."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)
        agent = _mock_agent(["hello", " world"])

        is_disconnected = AsyncMock(side_effect=[False, False, True])

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
        assert any(isinstance(event, SegmentDeltaEvent) for event in events)

        svc = TranslationStreamService(db_session)
        translation = db_session.execute(
            select(ChapterTranslation).where(ChapterTranslation.chapter_id == chapter.id)
        ).scalar_one()
        segment = db_session.execute(
            select(TranslationSegment).where(
                TranslationSegment.chapter_translation_id == translation.id
            )
        ).scalar_one()

        assert translation.status == "idle"
        assert segment.tgt == "hello"
        assert "partial" in (segment.flags or [])
        assert svc.needs_translation(segment) is True

    def test_resume_retranslates_partial_segment_and_clears_partial_flag(self, db_session):
        """Partial persisted text is retried and finalized on the next resume."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)

        svc = TranslationStreamService(db_session)
        translation = svc.get_or_create_translation(chapter.id)
        segment = svc.ensure_segments(translation, chapter.normalized_text)[0]
        segment.tgt = "hello"
        segment.flags = ["partial"]
        translation.status = "idle"
        db_session.add_all([translation, segment])
        db_session.commit()

        captured_contexts: list[list[dict[str, str]] | None] = []

        async def _stream(
            src,
            *,
            preceding_segments=None,
            instruction=None,
            current_translation=None,
        ):
            captured_contexts.append(preceding_segments)
            yield "finished"

        agent = MagicMock()
        agent.context_window = 3
        agent.model = "test-model"
        agent.stream_segment = MagicMock(side_effect=_stream)

        with patch.object(workflow, "_resolve_agent", return_value=agent):
            events = _run(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        assert any(isinstance(event, SegmentStartEvent) for event in events)
        assert isinstance(events[-1], TranslationCompleteEvent)

        db_session.expire_all()
        updated_translation = db_session.execute(
            select(ChapterTranslation).where(ChapterTranslation.id == translation.id)
        ).scalar_one()
        updated_segment = db_session.execute(
            select(TranslationSegment).where(TranslationSegment.id == segment.id)
        ).scalar_one()

        assert updated_translation.status == "completed"
        assert updated_segment.tgt == "finished"
        assert "partial" not in (updated_segment.flags or [])
        assert captured_contexts == [[]]

    def test_partial_persistence_is_throttled_across_many_deltas(self, db_session):
        """Rapid-fire deltas should not commit on every token; final text must still land."""
        from services import translation_workflow as tw

        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)
        tokens = [f"t{i}" for i in range(50)]
        agent = _mock_agent(tokens)

        persist_calls: list[str] = []
        original = workflow._stream_service.persist_partial_segment_translation

        def _tracking(segment, text):
            persist_calls.append(text)
            return original(segment, text)

        with (
            patch.object(workflow, "_resolve_agent", return_value=agent),
            patch.object(
                workflow._stream_service,
                "persist_partial_segment_translation",
                side_effect=_tracking,
            ),
            patch.object(tw, "PARTIAL_COMMIT_INTERVAL_S", 60.0),
        ):
            events = _run(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        # With a 60s throttle and a synchronous test loop, only the first delta
        # should pass the interval gate. The rest coalesce into segment-complete.
        assert len(persist_calls) == 1
        assert persist_calls[0] == "t0"

        assert any(isinstance(e, SegmentCompleteEvent) for e in events)
        segment = db_session.execute(
            select(TranslationSegment)
        ).scalars().first()
        assert segment.tgt == "".join(tokens)
        assert "partial" not in (segment.flags or [])

    def test_throttled_partial_is_flushed_on_cancel(self, db_session):
        """If cancel fires before throttle elapses, the collected text is flushed."""
        from services import translation_workflow as tw

        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "some text")
        workflow = TranslationWorkflow(db_session)
        agent = _mock_agent(["alpha", "beta", "gamma"])

        # side_effect: pre-loop check, delta1, delta2, cancel on delta3
        is_disconnected = AsyncMock(side_effect=[False, False, False, True])

        with (
            patch.object(workflow, "_resolve_agent", return_value=agent),
            patch.object(tw, "PARTIAL_COMMIT_INTERVAL_S", 60.0),
        ):
            _events, was_cancelled = _run_until_cancelled(
                workflow.start_or_resume(
                    chapter,
                    work.id,
                    prompt_override=None,
                    is_disconnected=is_disconnected,
                )
            )

        assert was_cancelled
        segment = db_session.execute(
            select(TranslationSegment)
        ).scalars().first()
        # First delta persisted by throttle; cancel fires on the third iteration,
        # after "alpha"+"beta" was collected. Flush-on-cancel must save that text.
        assert segment.tgt == "alphabeta"
        assert "partial" in (segment.flags or [])

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

    def test_preflight_segment_check_not_found(self, db_session):
        """Missing segment raises SegmentNotFoundError from preflight check."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work, "text")
        workflow = TranslationWorkflow(db_session)

        with pytest.raises(SegmentNotFoundError):
            workflow.preflight_segment_check(chapter, segment_id=99999)
