"""Workflow-level event sequence tests for ExplanationWorkflow."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.models import Chapter, TranslationSegment, Work
from services.exceptions import SegmentNotFoundError, SegmentNotTranslatedError
from services.explanation_workflow import (
    ExplanationCompleteEvent,
    ExplanationDeltaEvent,
    ExplanationErrorEvent,
    ExplanationWorkflow,
)
from services.translation_stream import TranslationStreamService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_work(session) -> Work:
    work = Work(title="Test Work", source="test", source_id="expl-test-work", source_meta={})
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
        text_hash="expl-test-hash",
    )
    session.add(chapter)
    session.commit()
    session.refresh(chapter)
    return chapter


def _setup_translated_segment(session, chapter: Chapter) -> TranslationSegment:
    svc = TranslationStreamService(session)
    translation = svc.get_or_create_translation(chapter.id)
    segments = svc.ensure_segments(translation, chapter.normalized_text)
    seg = next(s for s in segments if svc.needs_translation(s))
    seg.tgt = "translated text"
    session.add(seg)
    session.commit()
    session.refresh(seg)
    return seg


def _run(gen) -> list:
    async def _inner():
        events = []
        async for event in gen:
            events.append(event)
        return events

    return asyncio.run(_inner())


def _mock_explanation_agent(tokens: list[str] | None = None) -> MagicMock:
    if tokens is None:
        tokens = ["explanation chunk"]

    async def _stream(*args, **kwargs):
        for token in tokens:
            yield token

    agent = MagicMock()
    agent.model = "test-model"
    agent.stream_explanation = MagicMock(side_effect=_stream)
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExplanationWorkflowPreflightCheck:
    def test_not_found_raises(self, db_session):
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        workflow = ExplanationWorkflow(db_session)

        with pytest.raises(SegmentNotFoundError):
            workflow.preflight_check(chapter, segment_id=99999)

    def test_not_translated_raises(self, db_session):
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        workflow = ExplanationWorkflow(db_session)

        svc = TranslationStreamService(db_session)
        translation = svc.get_or_create_translation(chapter.id)
        segments = svc.ensure_segments(translation, chapter.normalized_text)
        untranslated = next(s for s in segments if svc.needs_translation(s))

        with pytest.raises(SegmentNotTranslatedError):
            workflow.preflight_check(chapter, untranslated.id)

    def test_returns_segment_on_success(self, db_session):
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        seg = _setup_translated_segment(db_session, chapter)
        workflow = ExplanationWorkflow(db_session)

        result = workflow.preflight_check(chapter, seg.id)
        assert result.id == seg.id


class TestExplainSegmentCold:
    def test_cold_path_event_sequence(self, db_session):
        """Cold path: ExplanationDeltaEvent(s) → ExplanationCompleteEvent; explanation saved."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        seg = _setup_translated_segment(db_session, chapter)
        workflow = ExplanationWorkflow(db_session)

        agent = _mock_explanation_agent(["part one", " part two"])
        with patch("services.explanation_workflow.get_explanation_agent", return_value=agent):
            events = _run(
                workflow.explain_segment(
                    chapter,
                    seg.id,
                    force=False,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        assert isinstance(events[0], ExplanationDeltaEvent)
        assert isinstance(events[-1], ExplanationCompleteEvent)
        assert events[-1].explanation == "part one part two"

        db_session.expire_all()
        updated = db_session.execute(
            select(TranslationSegment).where(TranslationSegment.id == seg.id)
        ).scalar_one()
        assert updated.explanation == "part one part two"


class TestExplainSegmentCached:
    def test_cached_path_skips_agent(self, db_session):
        """Cached explanation: full text as single delta + complete; agent not called."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        seg = _setup_translated_segment(db_session, chapter)
        seg.explanation = "cached explanation"
        db_session.add(seg)
        db_session.commit()

        workflow = ExplanationWorkflow(db_session)
        agent = _mock_explanation_agent()

        with patch("services.explanation_workflow.get_explanation_agent", return_value=agent):
            events = _run(
                workflow.explain_segment(
                    chapter,
                    seg.id,
                    force=False,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        assert len(events) == 2
        assert isinstance(events[0], ExplanationDeltaEvent)
        assert events[0].delta == "cached explanation"
        assert isinstance(events[1], ExplanationCompleteEvent)
        assert events[1].explanation == "cached explanation"
        agent.stream_explanation.assert_not_called()


class TestExplainSegmentForce:
    def test_force_clears_cache_and_regenerates(self, db_session):
        """force=True: cache is cleared, agent is called, fresh explanation saved."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        seg = _setup_translated_segment(db_session, chapter)
        seg.explanation = "old explanation"
        db_session.add(seg)
        db_session.commit()

        workflow = ExplanationWorkflow(db_session)
        agent = _mock_explanation_agent(["new explanation"])

        with patch("services.explanation_workflow.get_explanation_agent", return_value=agent):
            events = _run(
                workflow.explain_segment(
                    chapter,
                    seg.id,
                    force=True,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        assert isinstance(events[-1], ExplanationCompleteEvent)
        assert events[-1].explanation == "new explanation"
        agent.stream_explanation.assert_called_once()

        db_session.expire_all()
        updated = db_session.execute(
            select(TranslationSegment).where(TranslationSegment.id == seg.id)
        ).scalar_one()
        assert updated.explanation == "new explanation"


class TestExplainSegmentErrorPaths:
    def test_not_found_raises(self, db_session):
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        workflow = ExplanationWorkflow(db_session)

        with pytest.raises(SegmentNotFoundError):
            _run(
                workflow.explain_segment(
                    chapter,
                    segment_id=99999,
                    force=False,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

    def test_not_translated_raises(self, db_session):
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        workflow = ExplanationWorkflow(db_session)

        svc = TranslationStreamService(db_session)
        translation = svc.get_or_create_translation(chapter.id)
        segments = svc.ensure_segments(translation, chapter.normalized_text)
        untranslated = next(s for s in segments if svc.needs_translation(s))

        with pytest.raises(SegmentNotTranslatedError):
            _run(
                workflow.explain_segment(
                    chapter,
                    untranslated.id,
                    force=False,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

    def test_cancellation_propagates(self, db_session):
        """CancelledError propagates; explanation is NOT saved."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        seg = _setup_translated_segment(db_session, chapter)
        workflow = ExplanationWorkflow(db_session)

        # Two tokens so the second is_disconnected() call triggers cancellation
        agent = _mock_explanation_agent(["tok1", "tok2"])
        is_disconnected = AsyncMock(side_effect=[False, True])

        async def _run_until_cancelled():
            async for _ in workflow.explain_segment(
                chapter,
                seg.id,
                force=False,
                is_disconnected=is_disconnected,
            ):
                pass

        with patch("services.explanation_workflow.get_explanation_agent", return_value=agent):
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(_run_until_cancelled())

        db_session.expire_all()
        updated = db_session.execute(
            select(TranslationSegment).where(TranslationSegment.id == seg.id)
        ).scalar_one()
        assert updated.explanation is None

    def test_agent_error_emits_error_event(self, db_session):
        """Agent exception mid-stream yields ExplanationErrorEvent."""
        work = _make_work(db_session)
        chapter = _make_chapter(db_session, work)
        seg = _setup_translated_segment(db_session, chapter)
        workflow = ExplanationWorkflow(db_session)

        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("explainer exploded")
            yield  # make it an async generator

        agent = MagicMock()
        agent.model = "test-model"
        agent.stream_explanation = MagicMock(side_effect=_failing_stream)

        with patch("services.explanation_workflow.get_explanation_agent", return_value=agent):
            events = _run(
                workflow.explain_segment(
                    chapter,
                    seg.id,
                    force=False,
                    is_disconnected=AsyncMock(return_value=False),
                )
            )

        error_events = [e for e in events if isinstance(e, ExplanationErrorEvent)]
        assert error_events
        assert "explainer exploded" in error_events[0].error
