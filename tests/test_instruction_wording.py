"""Focused text checks for four decisions. Agent behavior is assessed separately."""

import re
import unittest

import test_skill_package as package


def section(filename, heading):
    path = package.checked_local_path(package.SKILL / filename, package.SKILL)
    prose = "\n".join(package.markdown_lines(path.read_text(encoding="utf-8")))
    level = len(heading.split()[0])
    boundary = rf"^#{{1,{level}}} |\Z"
    match = re.search(rf"^{re.escape(heading)}[^\n]*\n(.*?)(?={boundary})",
                      prose, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"Missing {heading} in {filename}")
    return match[1]


def words(text):
    return " ".join(text.lower().replace("**", "").split())


class DecisionWordingTests(unittest.TestCase):
    def test_tiny_fix_excludes_audit_report_and_new_structure(self):
        sizing = section("SKILL.md", "## Size the work before acting")
        tiny = re.search(r"^\| Tiny \|.*$", sizing, re.MULTILINE)
        self.assertIsNotNone(tiny, "The sizing table needs a Tiny row")
        control = "| Tiny | label correction | No audit. No architecture report. No new structure. |"
        for name, row in (("shipped", tiny[0]), ("allowed control", control)):
            with self.subTest(case=name):
                depth = words(row.rstrip().strip("|").split("|")[-1])
                for duty in ("audit", "architecture report", "new structure"):
                    self.assertIn("no " + duty, depth)

        existing = section("SKILL.md", "### Existing project")
        # The Tiny row and the existing-project instructions both describe this path.
        # A separate paragraph on substantial or architectural work may require a survey.
        tiny_path = re.search(r"^(?=[^\n]*\btiny\b).+?(?=^For (?:substantial|architectural)\b|^INSPECT →|\Z)",
                              existing, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(tiny_path, "Existing projects need an explicit tiny-fix path")
        scope = r"(?:whole|entire|full) (?:project|repo(?:sitory)?|codebase)"
        task = r"(?:(?:full|project-wide|repository-wide) )?(?:survey|audit|architectur(?:e|al) report)"
        ceremony = re.compile(
            rf"\b(?:(?:survey|audit|review|inspect) (?:the |an? )?{scope}"
            r"|(?:survey|audit) (?:the |this )(?:repo(?:sitory)?|codebase)\b"
            rf"|(?:conduct|perform|require|run|write|create|produce|prepare) (?:an? |the )?{task}"
            rf"|{task} (?:is|remains) (?:required|mandatory))\b"
        )
        allowed = ("Never survey the whole repository or write an architecture report. "
                   "No audit is required.")
        for instructions in (tiny[0], tiny_path[0], allowed):
            prose = words(instructions)
            previous_end = None
            for match in ceremony.finditer(prose):
                prefix = prose[:match.start()]
                prohibited = re.search(r"\b(?:no|not|never|avoid|skip|without|no need to) (?:ever )?$", prefix)
                continuation = previous_end is not None and prefix[previous_end:].strip() in ("or", "and")
                self.assertTrue(prohibited or continuation, f"Tiny path requires wider work: {match[0]}")
                previous_end = match.end()

    def test_standard_yields_to_owner_and_project_decisions(self):
        precedence = section("SKILL.md", "## Precedence")
        intro, members = precedence.split("\n- ", 1)
        self.assertIn("owner decisions", members)
        self.assertIn("repository-local instructions", members)
        self.assertIn("accepted ADRs", members)
        for name, lead in (("shipped", intro), ("allowed control", "This general standard defers to:")):
            with self.subTest(case=name):
                self.assertRegex(words(lead),
                                 r"\b(?:it|(?:this|the) (?:general )?standard) (?:yields|defers) to:$")

        # A correct list introduction does not cancel a conflicting instruction elsewhere in §61.
        standard = r"(?:this|the) (?:general |engineering |build )?standard"
        higher = r"\b(?:owner|project|repository|adr)s?\b"
        claims_priority = re.compile(
            rf"\b{standard} (?:(?:always|still|must|will|can|may) )*"
            r"(?:wins?|overrides?|takes? precedence|prevails?)\b"
        )
        allowed = ("In a conflict with this standard, the owner wins. "
                   "This standard must never override an accepted ADR. "
                   "Project instructions take precedence over this standard.")
        for instructions in (precedence, allowed):
            for sentence in re.split(r"[.!?;]", words(instructions)):
                claim = claims_priority.search(sentence)
                if claim and (re.search(higher, sentence) or sentence.strip() == claim[0]):
                    self.fail(f"Standard outranks owner or project authority: {sentence.strip()}")

    def test_inspect_unfamiliar_commands_before_running_them(self):
        baseline = section("SKILL.md", "### Before the first edit")
        control = "Before running an unfamiliar build command,\nreview the scripts, wrappers and hooks."
        for name, instructions in (("shipped", baseline), ("allowed control", control)):
            with self.subTest(case=name):
                self.assertRegex(words(instructions),
                                 r"\bbefore running an unfamiliar [^.!?]+?command, "
                                 r"(?:inspect|review) the scripts, wrappers and hooks\b")

    def test_screen_proof_cannot_be_waived(self):
        quality = section("references/frontend.md", "## §72 ")
        # The existing §72 test checks required widths and the fixed-screen exception.
        # Here a second instruction cannot authorize skipping that rendered proof.
        waiver = re.compile(
            r"\b(?:(?P<prohibition>never|do not|must not) )?"
            r"(?:(?:accept|approve|allow) (?:\w+ ){0,3}unrendered (?:layout|screen)s?"
            r"|(?:skip|waive|omit) (?:the |all )?(?:rendered layout|screen[- ]size) checks?)\b"
        )
        optional = r"\b(?:rendered layout|screen[- ]size) checks? (?:is|are) (?:optional|unnecessary)\b"
        control = ("Never accept an unrendered layout. Do not skip the rendered layout checks. "
                   "Screen-size checks are not optional.")
        for name, instructions in (("shipped", quality), ("allowed control", control)):
            with self.subTest(case=name):
                prose = words(instructions)
                self.assertNotRegex(prose, optional)
                for match in waiver.finditer(prose):
                    self.assertIsNotNone(match["prohibition"], f"Screen proof waived: {match[0]}")
