"""Generic reproductions of live retrieval contamination and quote shapes."""

from types import SimpleNamespace

from app import agent, corpus, research


def test_exact_routing_label_does_not_drag_incidental_candidates(monkeypatch):
    def entry(title, labels, text):
        return {"titre": title, "centre": "Test", "url": "https://example.invalid/" + title,
                "kws": labels, "passages": [text]}
    monkeypatch.setattr(corpus, "CORPUS", {
        "subject": entry("Calendrier", ["calendrier lunaire"], "Dates et observation de la lune."),
        "decoy": entry("Jardinage", ["calendrier jardinage"], "Le calendrier accompagne les familles."),
    })
    docs = corpus.corpus_search(["calendrier", "lunaire", "familles"])
    assert [doc.centre_id for doc in docs] == ["corpus-subject"]


def test_live_adjacent_subject_does_not_retrieve_unrelated_specialist_packet():
    question = "Je suis assistante sociale : comment orienter et accompagner cet adolescent atteint de la maladie de Charcot ?"
    docs = corpus.corpus_search(research.keywords(question, []))
    assert "corpus-sla" in {doc.centre_id for doc in docs}
    assert not any(doc.centre_id.startswith("corpus-genetic_") for doc in docs)


def test_contact_quote_array_preserves_exact_provenance():
    quote = "Le centre de référence SLA accompagne les personnes concernées."
    doc = SimpleNamespace(titre="PNDS SLA", passages=[quote], url="https://www.has-sante.fr/")
    raw = {"contacts": [{"nom": "Centre de référence SLA", "role": quote,
                         "source_id": 1, "quote": [quote]}]}
    answer = agent._clean(raw, [doc])
    assert answer["contacts"] == [{"nom": "Centre de référence SLA", "role": quote + " [1]",
                                   "scope": "National", "url": doc.url}]


def test_contact_array_does_not_rescue_nonliteral_quote():
    doc = SimpleNamespace(titre="PNDS", passages=["Le centre accueille les familles."], url="https://www.has-sante.fr/")
    raw = {"contacts": [{"nom": "Centre", "role": "Le centre verse 1000 €.",
                         "source_id": 1, "quote": ["Le centre verse 1000 €."]}]}
    assert agent._clean(raw, [doc])["contacts"] == []
