import json
import unittest

from ovos_bus_client.session import Session
from ovos_commonqa.opm import CommonQAService
from ovos_tskill_fakewiki import FakeWikiSkill
from ovos_utils.messagebus import FakeBus, Message


class TestCommonQuery(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.bus.emitted_msgs = []

        def get_msg(msg):
            self.bus.emitted_msgs.append(json.loads(msg))

        self.skill = FakeWikiSkill()
        self.skill._startup(self.bus, "wiki.test")

        self.cc = CommonQAService(self.bus)

        self.bus.on("message", get_msg)

    def test_init(self):
        self.assertEqual(self.cc.bus, self.bus)
        self.assertIsInstance(self.cc.skill_id, str)
        self.assertIsInstance(self.cc.active_queries, dict)
        self.assertEqual(len(self.bus.ee.listeners("question:query.response")),
                         1)
        self.assertEqual(len(self.bus.ee.listeners("common_query.question")), 1)

    def test_is_question_like(self):
        lang = "en-US"
        self.assertTrue(self.cc.is_question_like("what is a computer", lang))
        self.assertTrue(self.cc.is_question_like("tell me about computers",
                                                 lang))
        self.assertFalse(self.cc.is_question_like("what computer", lang))
        self.assertFalse(self.cc.is_question_like("play something", lang))
        self.assertFalse(self.cc.is_question_like("play some music", lang))

    def test_match(self):
        # TODO
        pass

    def test_handle_question(self):
        # TODO
        pass

    def test_handle_query_response(self):
        # TODO
        pass

    def test_query_timeout(self):
        # TODO
        pass

    def test_match_with_none_blacklists(self):
        """Regression: under ovos-bus-client>=2.4 a Session may carry None for
        omitted blacklist collections (OVOS-SESSION-1 omission rule). The
        answer/select/speak path in handle_question, handle_query_response and
        _query_timeout iterates and membership-tests session.blacklisted_skills,
        so a None must not raise TypeError and break the whole match flow.

        SessionManager.get rebuilds the session from the message, so the None
        is injected by patching it to return a Session whose blacklists are
        None -- mirroring what a bus-client variant / in-memory session can
        hand the plugin."""
        from unittest.mock import patch
        from ovos_bus_client.session import SessionManager

        sess = Session("test-none-bl")
        # the bug condition: blacklists are None, not empty lists
        sess.blacklisted_skills = None
        sess.blacklisted_intents = None

        utt = "what is the speed of light"
        message = Message("recognizer_loop:utterance",
                          {"utterances": [utt], "lang": "en-US"},
                          {"session": {"session_id": "test-none-bl"}})

        # full match -> handle_question -> handle_query_response ->
        # _query_timeout select path must complete and produce an answer,
        # never a 'NoneType' object is not iterable TypeError
        with patch.object(SessionManager, "get", return_value=sess):
            match = self.cc.match([utt], "en-US", message)

        self.assertIsNotNone(match,
                             "answer/select flow did not complete with "
                             "None blacklists")
        self.assertEqual(match.skill_id, "wiki.test")
        self.assertEqual(match.match_data["answer"], "answer 1")
        # the query path tore down cleanly (no leaked active query)
        self.assertEqual(len(self.cc.active_queries), 0)

    def test_common_query_events(self):
        self.bus.emitted_msgs = []
        self.assertEqual(self.cc.skill_id, "common_query.openvoiceos")

        qq_ctxt = {"source": "audio",
                   "destination": "skills",
                   'skill_id': self.cc.skill_id}
        qq_ans_ctxt = {"source": "skills",
                       "destination": "audio",
                       'skill_id': self.cc.skill_id}
        original_ctxt = dict(qq_ctxt)
        self.bus.emit(Message("common_query.question",
                              {"utterance": "what is the speed of light"},
                              dict(qq_ctxt)))
        self.assertEqual(qq_ctxt, original_ctxt, qq_ctxt)
        skill_ctxt = {"source": "audio", "destination": "skills", 'skill_id': 'wiki.test'}
        skill_ans_ctxt = {"source": "skills", "destination": "audio", 'skill_id': 'wiki.test'}

        expected = [
            # original query
            {'context': qq_ctxt,
             'data': {'utterance': 'what is the speed of light'},
             'type': 'common_query.question'},
            # thinking animation
            {'type': 'enclosure.mouth.think',
             'data': {},
             'context': qq_ctxt},
            # send query
            {'type': 'question:query',
             'data': {'phrase': 'what is the speed of light'},
             'context': qq_ans_ctxt},
            # skill announces its searching
            {'type': 'question:query.response',
             'data': {'phrase': 'what is the speed of light',
                      'skill_id': 'wiki.test',
                      'searching': True},
             'context': skill_ctxt},
            # skill context set by skill for continuous dialog
            {'type': 'add_context',
             'data': {'context': 'wiki_testFakeWikiKnows',
                      'word': 'what is the speed of light',
                      'origin': ''},
             'context': skill_ans_ctxt},
            # final response
            {'type': 'question:query.response',
             'data': {'phrase': 'what is the speed of light',
                      'skill_id': 'wiki.test',
                      'answer': "answer 1",
                      'handles_speech': True,
                      'callback_data': {'query': 'what is the speed of light',
                                        'answer': "answer 1"},
                      'conf': 0.74},
             'context': skill_ctxt},
            # stop thinking animation
            {'type': 'enclosure.mouth.reset',
             'data': {},
             'context': qq_ctxt}
        ]

        for ctr, msg in enumerate(expected):
            print(ctr, msg)
            m: dict = self.bus.emitted_msgs[ctr]
            if "session" in m.get("context", {}):
                m["context"].pop("session")  # simplify test comparisons
            if "session" in msg.get("context", {}):
                msg["context"].pop("session")  # simplify test comparisons
            self.assertEqual(msg, m, f"idx={ctr}|emitted={m}")
