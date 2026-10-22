import threading
import time
import unittest

from ovos_commonqa.opm import CommonQAService
from ovos_utils.messagebus import FakeBus, Message


class TestCollectionCeiling(unittest.TestCase):
    """OVOS-COMMON-QUERY-1 §7.2: the plugin MUST enforce the ceiling.

    A claimant that keeps reporting `searching` extends the window, but
    only up to the ceiling (`max_response_wait`), never beyond it.
    """

    MAX_WAIT = 1.0
    SEARCHING_FOR = 4.0

    def setUp(self):
        self.bus = FakeBus()
        self.cc = CommonQAService(self.bus, config={
            "max_response_wait": self.MAX_WAIT,
            "extension_time": 0.5,
            "reranker": "none",
        })
        self.cc.common_query_skills = ["slow.skill"]
        self.stop = threading.Event()
        self.bus.on("question:query", self._keep_searching)

    def tearDown(self):
        self.stop.set()
        self.cc.shutdown()

    def _keep_searching(self, message):
        message = Message.deserialize(message) if isinstance(message, str) else message

        def spam():
            end = time.time() + self.SEARCHING_FOR
            while time.time() < end and not self.stop.is_set():
                self.bus.emit(message.response({"phrase": message.data["phrase"],
                                                "skill_id": "slow.skill",
                                                "searching": True}))
                time.sleep(0.2)

        threading.Thread(target=spam, daemon=True).start()

    def test_extensions_stop_at_the_ceiling(self):
        start = time.time()
        answered, _ = self.cc.handle_question(
            Message("common_query.question", {"utterance": "what is the speed of light"}))
        elapsed = time.time() - start
        self.assertFalse(answered)
        # the poll loop checks every 0.1 s; allow scheduling slack, but far
        # less than the SEARCHING_FOR seconds an unbounded window waits
        self.assertLess(elapsed, self.MAX_WAIT + 0.6,
                        f"collection took {elapsed:.2f}s, ceiling is {self.MAX_WAIT}s")


class TestExtensionNeverShortensTheWindow(unittest.TestCase):
    """OVOS-COMMON-QUERY-1 §7.2: the window closes early only when no claimant
    is outstanding. A skill that reported `searching` is outstanding, so its
    extension must not move the deadline earlier than it already was."""

    MAX_WAIT = 4.0

    def setUp(self):
        self.bus = FakeBus()
        self.cc = CommonQAService(self.bus, config={
            "max_response_wait": self.MAX_WAIT,
            "extension_time": 0.5,
            "reranker": "none",
        })
        self.cc.common_query_skills = ["late.skill"]
        self.bus.on("question:query", self._search_then_answer)

    def tearDown(self):
        self.cc.shutdown()

    def _search_then_answer(self, message):
        message = Message.deserialize(message) if isinstance(message, str) else message
        phrase = message.data["phrase"]

        def respond():
            time.sleep(0.1)
            self.bus.emit(message.response({"phrase": phrase, "skill_id": "late.skill",
                                            "searching": True}))
            time.sleep(0.8)  # answers at 0.9 s, after the 0.5 s extension
            self.bus.emit(message.response({"phrase": phrase, "skill_id": "late.skill",
                                            "answer": "about 300000 km/s",
                                            "conf": 0.9}))

        threading.Thread(target=respond, daemon=True).start()

    def test_answer_after_an_early_extension_is_collected(self):
        start = time.time()
        _, query = self.cc.handle_question(
            Message("common_query.question", {"utterance": "what is the speed of light"}))
        elapsed = time.time() - start
        answered_by = [r.get("skill_id") for r in query.replies]
        self.assertIn("late.skill", answered_by,
                      f"collection closed at {elapsed:.2f}s before the answer at 0.9s")


if __name__ == "__main__":
    unittest.main()
