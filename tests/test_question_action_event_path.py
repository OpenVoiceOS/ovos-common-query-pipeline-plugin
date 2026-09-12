"""Regression tests for the ``common_query.question`` bus-event path.

The intent service can reach ``CommonQAService.handle_question`` two ways:

- via the pipeline-stage ``match()`` method, which runs the contest and
  returns an ``IntentHandlerMatch`` the service dispatches -- the answer
  reaches the winning skill through the returned match;
- via the ``common_query.question`` bus event, which the intent service
  dispatches when a pipeline plugin (e.g. ovos-m2v-pipeline) classifies an
  utterance as ``common_query:common_query`` and remaps it to
  ``common_query.question`` with ``skill_id="common_query.openvoiceos"``.

A bus event handler's return value is discarded, so the event path can only
complete if ``handle_question`` itself emits the winning skill's dispatch.
``_query_timeout`` emitted ``question:action`` itself until it was moved into
``match()``'s return value; since then the event path runs the full contest,
selects an answer, and silently drops it -- the user hears nothing.
"""

import json
import unittest

from ovos_bus_client.message import Message
from ovos_tskill_fakewiki import FakeWikiSkill
from ovos_utils.fakebus import FakeBus

from ovos_commonqa.opm import CommonQAService


class TestQuestionActionEventPath(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.bus.emitted_msgs = []

        def get_msg(msg):
            self.bus.emitted_msgs.append(json.loads(msg))

        self.skill = FakeWikiSkill()
        self.skill._startup(self.bus, "wiki.test")

        self.cc = CommonQAService(self.bus)

        self.bus.on("message", get_msg)

    def _emitted_types(self):
        return [m["type"] for m in self.bus.emitted_msgs]

    def test_event_path_emits_completing_question_action(self):
        """A question dispatched as the common_query.question bus event must
        end with the winning skill's question:action dispatch on the bus.
        The fake skill is a classic CommonQuerySkill, so the old-style topic
        (no skill_id suffix) is the expected shape."""
        msg = Message("common_query.question",
                      {"utterance": "what is the speed of light"},
                      {"source": "audio", "destination": "skills",
                       "skill_id": "common_query.openvoiceos"})
        self.bus.emit(msg)

        types = self._emitted_types()
        self.assertIn("question:action", types,
                      f"no completing dispatch on the bus; got: {types}")

    def test_event_path_dispatch_reaches_winning_skill(self):
        """The completing dispatch carries the winning skill's answer so its
        registered question:action.<skill_id> handler can speak it. The fake
        skill stands in for ovos-workshop's __handle_query_action: it reads
        data["skill_id"] and re-emits the suffixed topic, exactly as the
        workshop skill does for a classic CommonQuerySkill."""
        spoken = []

        def workshop_reemit(message):
            if message.data.get("skill_id") != "wiki.test":
                return
            message.msg_type += ".wiki.test"
            self.bus.emit(message)

        self.bus.on("question:action", workshop_reemit)
        self.bus.on("question:action.wiki.test",
                    lambda m: spoken.append(m))

        msg = Message("common_query.question",
                      {"utterance": "what is the speed of light"},
                      {"source": "audio", "destination": "skills",
                       "skill_id": "common_query.openvoiceos"})
        self.bus.emit(msg)

        self.assertEqual(len(spoken), 1,
                         f"winning skill never received its dispatch; "
                         f"emitted: {self._emitted_types()}")
        self.assertEqual(spoken[0].data.get("answer"), "answer 1")
        self.assertEqual(spoken[0].data.get("phrase"),
                         "what is the speed of light")
        self.assertEqual(spoken[0].context.get("skill_id"), "wiki.test")

    def test_event_path_no_double_dispatch_after_match(self):
        """match() consumes the contest result through its return value, so
        it must not also emit the dispatch on the bus (the skill would speak
        twice)."""
        utt = "what is the speed of light"
        message = Message("recognizer_loop:utterance",
                          {"utterances": [utt], "lang": "en-US"},
                          {"session": {"session_id": "test-no-double"}})

        match = self.cc.match([utt], "en-US", message)

        self.assertIsNotNone(match)
        types = self._emitted_types()
        self.assertNotIn("question:action", types)

    def test_event_path_no_answer_no_dispatch(self):
        """When no skill answers, no dispatch is emitted."""
        self.skill.ask_the_wiki = lambda query: []  # no results

        msg = Message("common_query.question",
                      {"utterance": "what is the speed of light"},
                      {"source": "audio", "destination": "skills",
                       "skill_id": "common_query.openvoiceos"})
        self.bus.emit(msg)

        types = self._emitted_types()
        self.assertNotIn("question:action.wiki.test", types)

    def test_event_path_teardown_active_queries(self):
        """The event path does not leak an active query entry."""
        msg = Message("common_query.question",
                      {"utterance": "what is the speed of light"},
                      {"source": "audio", "destination": "skills",
                       "skill_id": "common_query.openvoiceos"})
        self.bus.emit(msg)

        self.assertEqual(len(self.cc.active_queries), 0)

    def test_match_path_still_works(self):
        """The pipeline-stage match() path keeps returning the completing
        IntentHandlerMatch as before -- the fix must not double-dispatch on
        the bus there, or the winning skill's handler would fire twice."""
        utt = "what is the speed of light"
        message = Message("recognizer_loop:utterance",
                          {"utterances": [utt], "lang": "en-US"},
                          {"session": {"session_id": "test-match-path"}})

        match = self.cc.match([utt], "en-US", message)

        self.assertIsNotNone(match)
        # the fake skill is a classic CommonQuerySkill, so the old-style
        # topic (no skill_id suffix) is the correct pre-existing shape here
        self.assertEqual(match.match_type, "question:action")
        self.assertEqual(match.skill_id, "wiki.test")
        self.assertEqual(match.match_data["answer"], "answer 1")


if __name__ == "__main__":
    unittest.main()
