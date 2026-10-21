"""
Section 39's formal retrieval evaluation set: 40 representative queries
covering every category, several intentionally hard paraphrases, and a
set of clearly off-domain queries that must fall back. This replaces the
informal 18-query check used to pick the Phase 6 threshold with a wider,
documented set — see tests/test_evaluation.py for how it's scored.

Each entry is one of:
  {"query": ..., "expect": "confident", "expected_category": "..."}
  {"query": ..., "expect": "fallback"}

Queries are paraphrased, not copied verbatim from canonical_question,
except where noted — verbatim queries are trivial near-1.0 self-matches
and don't test generalization, so most entries deliberately reword the
real FAQ content instead.
"""

EVALUATION_QUERIES = [
    # --- One on-domain query per category (16) ---
    {
        "query": "What does it mean to be admitted to college?",
        "expect": "confident",
        "expected_category": "Admissions Fundamentals",
    },
    {
        "query": "What's the process for applying to a university in the US?",
        "expect": "confident",
        "expected_category": "Application Process",
    },
    {
        "query": "What paperwork do I need to submit with my application?",
        "expect": "confident",
        "expected_category": "Application Requirements",
    },
    {
        "query": "What is Early Decision?",
        "expect": "confident",
        "expected_category": "Decision Types",
    },
    {
        "query": "Do colleges require the ACT?",
        "expect": "confident",
        "expected_category": "Testing",
    },
    {
        "query": "How long should my college essay be?",
        "expect": "confident",
        "expected_category": "Essays & Recommendations",
    },
    {
        "query": "Can students from other countries apply to US colleges?",
        "expect": "confident",
        "expected_category": "International Students",
    },
    {
        "query": "What exactly is a grant?",
        "expect": "confident",
        "expected_category": "Financial Aid",
    },
    {
        "query": "What is a full-ride scholarship?",
        "expect": "confident",
        "expected_category": "Scholarships & Funding",
    },
    {
        "query": "Does full funding cover every single cost?",
        "expect": "confident",
        "expected_category": "Full Funding",
    },
    {
        "query": "What is a gap year?",
        "expect": "confident",
        "expected_category": "Gap Years",
    },
    {
        "query": "How do I decide which colleges to apply to?",
        "expect": "confident",
        "expected_category": "College Selection",
    },
    {
        "query": "How can I keep track of application deadlines?",
        "expect": "confident",
        "expected_category": "Application Strategy",
    },
    {
        "query": "What should I do once I've been accepted?",
        "expect": "confident",
        "expected_category": "After Admission",
    },
    {
        "query": "How do I know if a scholarship offer is a scam?",
        "expect": "confident",
        "expected_category": "Safety & Verification",
    },
    {
        "query": "What is Harvard's current acceptance rate?",
        "expect": "confident",
        "expected_category": "Dynamic College Information",
    },
    # --- Paraphrase stress tests (harder rewordings, 8) ---
    {
        "query": "Can I still go to university after taking a year off?",
        "expect": "confident",
        "expected_category": "Gap Years",
    },
    {
        "query": "Is it possible to enroll in college after a year away from school?",
        "expect": "confident",
        "expected_category": "Gap Years",
    },
    {
        "query": "How can students from abroad get money to help pay for school?",
        "expect": "confident",
        "expected_category": "International Students",
    },
    {
        "query": "Is submitting standardized test scores required or optional?",
        "expect": "confident",
        "expected_category": "Testing",
    },
    {
        "query": "What's the difference between applying early and applying regular?",
        "expect": "confident",
        "expected_category": "Decision Types",
    },
    {
        "query": "How do colleges decide whether to admit an applicant?",
        "expect": "confident",
        "expected_category": "Admissions Fundamentals",
    },
    {
        "query": "What is the CSS Profile used for?",
        "expect": "confident",
        "expected_category": "International Students",
    },
    {
        "query": "Where can I check if a college's cost of attendance changed?",
        "expect": "confident",
        "expected_category": "Dynamic College Information",
    },
    # --- Clearly off-domain queries (must fall back, 12) ---
    {"query": "What is the capital of France?", "expect": "fallback"},
    {"query": "Who won the World Cup?", "expect": "fallback"},
    {"query": "Write me a Python game.", "expect": "fallback"},
    {"query": "What is Bitcoin?", "expect": "fallback"},
    {"query": "What is the weather today?", "expect": "fallback"},
    {"query": "Tell me a joke.", "expect": "fallback"},
    {"query": "How do I bake a cake?", "expect": "fallback"},
    {"query": "What time is it?", "expect": "fallback"},
    {"query": "Can you recommend a good movie?", "expect": "fallback"},
    {"query": "What is the tallest mountain in the world?", "expect": "fallback"},
    {"query": "How do I fix a flat tire?", "expect": "fallback"},
    {"query": "Translate 'hello' into Spanish.", "expect": "fallback"},
    # --- Short / ambiguous / edge-case queries (4) ---
    {"query": "SAT?", "expect": "confident", "expected_category": "Testing"},
    {
        "query": "deadlines",
        "expect": "confident",
        "expected_category": "Application Strategy",
    },
    {"query": "help", "expect": "fallback"},
    {"query": "college", "expect": "fallback"},
]
