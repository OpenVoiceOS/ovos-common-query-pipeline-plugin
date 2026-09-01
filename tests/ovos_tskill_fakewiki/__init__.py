"""Minimal bus-only CommonQuery skill stand-in used by the test suite.

The real common-query skills are ovos-workshop ``CommonQuerySkill`` subclasses,
but the pipeline plugin only ever talks to them over the messagebus. This fake
reproduces exactly the bus traffic a workshop CommonQuery skill emits in
response to ``question:query`` / ``ovos.common_query.ping`` so the pipeline can
be exercised without pulling in ovos-workshop as a test dependency.
"""
from ovos_bus_client.message import Message


class FakeWikiSkill:
    """Emulates a CommonQuery skill purely via the messagebus."""

    def __init__(self):
        self.bus = None
        self.skill_id = None
        self.displayed = False
        self.idx = 0
        self.results = []

    def _startup(self, bus, skill_id="ovos-tskill-fakewiki.openvoiceos"):
        self.bus = bus
        self.skill_id = skill_id
        self.bus.on("question:query", self.handle_query_phrase)
        self.bus.on("ovos.common_query.ping", self.handle_ping)
        # announce ourselves to a pipeline that is already running
        self.bus.emit(Message("ovos.common_query.pong",
                              {"skill_id": self.skill_id,
                               "is_classic_cq": True}))

    def handle_ping(self, message):
        self.bus.emit(message.reply("ovos.common_query.pong",
                                    {"skill_id": self.skill_id,
                                     "is_classic_cq": True},
                                    {"skill_id": self.skill_id}))

    def ask_the_wiki(self, query):
        self.idx = 0
        self.results = ["answer 1", "answer 2"]
        return self.results

    def handle_query_phrase(self, message):
        """Mirror CommonQuerySkill.__handle_question_query bus output."""
        search_phrase = message.data["phrase"]
        # signal that we are searching
        self.bus.emit(message.response({"phrase": search_phrase,
                                        "skill_id": self.skill_id,
                                        "searching": True},
                                       {"skill_id": self.skill_id}))

        answer = self.ask_the_wiki(search_phrase)[0]
        # context for follow up questions ("tell me more"); the workshop skill
        # munges the context name with an alnum form of the skill_id
        munged = self.skill_id.replace(".", "_").replace("-", "_")
        self.bus.emit(Message("add_context",
                              {"context": f"{munged}FakeWikiKnows",
                               "word": search_phrase,
                               "origin": ""},
                              {"skill_id": self.skill_id,
                               "source": "skills",
                               "destination": "audio"}))

        callback = {"query": search_phrase, "answer": answer}
        # GENERAL match level (0.5) + length bonus → 0.74, matching the
        # workshop skill's confidence calculation for this phrase/answer
        self.bus.emit(message.response({"phrase": search_phrase,
                                        "skill_id": self.skill_id,
                                        "answer": answer,
                                        "handles_speech": True,
                                        "callback_data": callback,
                                        "conf": 0.74},
                                       {"skill_id": self.skill_id}))


def create_skill():
    return FakeWikiSkill()
