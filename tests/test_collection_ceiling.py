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


if __name__ == "__main__":
    unittest.main()
