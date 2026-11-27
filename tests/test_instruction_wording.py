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
