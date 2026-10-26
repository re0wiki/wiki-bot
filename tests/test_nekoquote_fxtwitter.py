"""FxTwitter v2 时间线采集（离线）。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.nekoquote import fxtwitter


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params.copy(), timeout))
        return self.responses.pop(0)


def status(tid, text="正文", *, author="nezumiironyanko", reposted=False, created=100):
    return {
        "type": "status",
        "id": str(tid),
        "text": text,
        "created_timestamp": created,
        "author": {"screen_name": author},
        "reposted_by": {"screen_name": "nezumiironyanko"} if reposted else None,
    }


def page(results, *, bottom=None, code=200):
    return FakeResponse(
        200, {"code": code, "results": results, "cursor": {"bottom": bottom}}
    )


def test_fetch_quotes_accepts_author_originals_and_long_text():
    long_text = "数千字长文\n～Fin～"
    session = FakeSession(
        [
            page(
                [
                    status(3, long_text, created=300),
                    status(4, "自己的转推", reposted=True, created=400),
                    status(5, "别人的内容", author="other", created=500),
                    status(2, "", created=200),
                ]
            )
        ]
    )

    quotes, newest = fxtwitter.fetch_quotes(session)

    assert quotes == {"3": long_text}
    assert newest == "3"
    assert session.calls == [
        (
            fxtwitter.TIMELINE_URL,
            {"count": 100, "with_replies": "1"},
            60,
        )
    ]


def test_fetch_quotes_follows_cursor_and_deduplicates():
    session = FakeSession(
        [
            page([status(3, "首版", created=300)], bottom="older"),
            page([status(3, "重复项", created=300), status(2, "较早", created=200)]),
        ]
    )

    quotes, newest = fxtwitter.fetch_quotes(session)

    assert quotes == {"3": "首版", "2": "较早"}
    assert newest == "3"
    assert [call[1] for call in session.calls] == [
        {"count": 100, "with_replies": "1"},
        {"count": 100, "with_replies": "1", "cursor": "older"},
    ]


def test_fetch_quotes_stops_at_previous_original():
    session = FakeSession(
        [
            page(
                [
                    status(3, "新推", created=300),
                    status(2, "边界", created=200),
                    status(1),
                ],
                bottom="must-not-fetch",
            )
        ]
    )

    quotes, newest = fxtwitter.fetch_quotes(session, stop_id="2")

    assert quotes == {"3": "新推"}
    assert newest == "3"
    assert len(session.calls) == 1


def test_fetch_quotes_stops_before_migration_cutoff():
    session = FakeSession(
        [
            page(
                [status(3, "迁移期新推", created=300), status(1, "过旧", created=100)],
                bottom="must-not-fetch",
            )
        ]
    )

    quotes, newest = fxtwitter.fetch_quotes(session, stop_before=150)

    assert quotes == {"3": "迁移期新推"}
    assert newest == "3"
    assert len(session.calls) == 1


def test_fetch_quotes_accepts_204_empty_timeline():
    session = FakeSession([FakeResponse(204)])

    assert fxtwitter.fetch_quotes(session) == ({}, None)
    assert len(session.calls) == 1


def test_fetch_quotes_preserves_progress_before_204():
    session = FakeSession(
        [page([status(3, created=300)], bottom="older"), FakeResponse(204)]
    )

    assert fxtwitter.fetch_quotes(session) == ({"3": "正文"}, "3")
    assert len(session.calls) == 2


def test_fetch_quotes_stops_on_empty_page():
    session = FakeSession([page([], bottom="must-not-fetch")])

    assert fxtwitter.fetch_quotes(session) == ({}, None)
    assert len(session.calls) == 1


def test_fetch_quotes_rejects_repeated_cursor():
    session = FakeSession(
        [
            page([status(3)], bottom="same"),
            page([status(2)], bottom="same"),
        ]
    )

    with pytest.raises(RuntimeError, match="游标重复"):
        fxtwitter.fetch_quotes(session)


def test_fetch_quotes_rejects_error_payload():
    session = FakeSession([page([], code=500)])

    with pytest.raises(RuntimeError, match="code=500"):
        fxtwitter.fetch_quotes(session)


def test_latest_original_id_skips_reposts():
    session = FakeSession([page([status(9, reposted=True), status(7, "")])])

    assert fxtwitter.latest_original_id(session) == "7"
    assert len(session.calls) == 1


@pytest.mark.parametrize("kwargs", [{"stop_id": "2"}, {"stop_before": 150}])
def test_fetch_quotes_processes_entire_boundary_page(kwargs):
    session = FakeSession(
        [
            page(
                [
                    status(3, "新推", created=300),
                    status(2, "边界", created=100),
                    status(4, "页内乱序新推", created=400),
                ],
                bottom="must-not-fetch",
            )
        ]
    )

    quotes, newest = fxtwitter.fetch_quotes(session, **kwargs)

    assert quotes == {"3": "新推", "4": "页内乱序新推"}
    assert newest == "4"
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    ("responses", "kwargs"),
    [
        ([FakeResponse(204)], {"stop_id": "2"}),
        ([page([], bottom="unused")], {"stop_id": "2"}),
        ([page([status(3, created=300)])], {"stop_id": "2"}),
        ([page([status(3, created=300)])], {"stop_before": 150}),
        ([FakeResponse(204)], {"stop_before": 150}),
        ([page([], bottom="unused")], {"stop_before": 150}),
    ],
)
def test_fetch_quotes_rejects_incomplete_boundary_traversal(responses, kwargs):
    session = FakeSession(responses)

    with pytest.raises(RuntimeError, match="未抵达"):
        fxtwitter.fetch_quotes(session, **kwargs)


def test_latest_original_id_uses_numeric_maximum_across_pages():
    session = FakeSession(
        [
            page([status(9)], bottom="older"),
            page([status(10)], bottom="older-still"),
            page([status(8)]),
        ]
    )

    assert fxtwitter.latest_original_id(session) == "10"
    assert len(session.calls) == 3
