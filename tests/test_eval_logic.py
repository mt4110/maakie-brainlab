import unittest
from eval.run_eval import analyze_result, ReasonCode

class TestEvalLogic(unittest.TestCase):

    def test_parse_sources_strict(self):
        # Case 1: Standard valid source
        q = {"id": "T01", "expected_source": "hello.md#chunk-0"}
        ans = "結論:\n- 答え\n\n参照:\n- hello.md#chunk-0"
        res = analyze_result(q, ans, 0, "")
        self.assertTrue(res["passed"])
        self.assertIsNone(res["reason_code"])

        # Case 2: Source in text but not in reference block -> FAIL (NO_SOURCES or MISSING_REQUIRED_SOURCE)
        # Note: If no reference block is found, it is NO_SOURCES.
        ans_fake = "参照: はありませんが hello.md#chunk-0 に書いてあります。"
        res = analyze_result(q, ans_fake, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.NO_SOURCES)

        # Case 3: Partial match (file-level expectation vs chunk-level answer)
        q2 = {"id": "T02", "expected_source": "hello.md"}
        ans2 = "参照:\n- hello.md#chunk-99"
        res = analyze_result(q2, ans2, 0, "")
        self.assertTrue(res["passed"])

    def test_evidence_mode_any_vs_all(self):
        # Case 1: Normal (ANY) - 1 out of 3 is enough
        q_normal = {
            "id": "T11", 
            "type": "normal", 
            "expected_evidence": ["EvA", "EvB", "EvC"]
        }
        ans_partial = "結論:\n- ここに EvB があります。\n\n参照:\n- doc.md#chunk-1"
        res = analyze_result(q_normal, ans_partial, 0, "")
        self.assertTrue(res["passed"])

        # Case 2: Boundary (ALL) - 1 out of 3 is NOT enough
        q_bound = {
            "id": "T12", 
            "type": "boundary", 
            "expected_evidence": ["EvA", "EvB", "EvC"]
        }
        res = analyze_result(q_bound, ans_partial, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.MISSING_EXPECTED_EVIDENCE)
        self.assertEqual(res["details"]["missing_evidence"], ["EvA", "EvC"])

        # Case 3: Boundary (ALL) - All present
        ans_full = "結論:\n- EvAとEvBとEvCが揃っています。\n\n参照:\n- doc.md#chunk-1"
        res = analyze_result(q_bound, ans_full, 0, "")
        self.assertTrue(res["passed"])

    def test_unknown_detection_strict(self):
        # Case 1: Unknown in Conclusion -> FAIL (UNKNOWN_ANSWER)
        q = {"id": "T21", "type": "normal"}
        ans = "結論:\n- 不明です。\n\n参照:\n- 不明"
        res = analyze_result(q, ans, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.UNKNOWN_ANSWER)

        # Case 2: Unknown token in body text but Conclusion is fine -> PASS
        # (e.g. "unknown이라는 단어는...")
        # Note: Must include Sources to pass NO_SOURCES check
        ans_safe = "結論:\n- これはペンです。\n\n解説:\n- 英語ではunknownと言います。\n\n参照:\n- doc.md#chunk-1"
        res = analyze_result(q, ans_safe, 0, "")
        self.assertTrue(res["passed"])

    def test_negative_control_strict(self):
        q = {"id": "T31", "type": "negative_control"}

        # Case 1: Unknown/NoSources -> PASS
        ans_unknown = "結論:\n- 不明です。\n\n参照:\n- 不明"
        res = analyze_result(q, ans_unknown, 0, "")
        self.assertTrue(res["passed"])

        # Case 2: Has Sources -> FAIL (Positive Hallucination)
        ans_hallu = "結論:\n- 答えです。\n\n参照:\n- hello.md#chunk-0"
        res = analyze_result(q, ans_hallu, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.POSITIVE_HALLUCINATION)

        # Case 3: "However" logic in Conclusion -> FAIL (Mixed Hallucination)
        ans_mixed = "結論:\n- 不明ですが、一般的にはこうです。\n\n参照:\n- 不明"
        res = analyze_result(q, ans_mixed, 0, "")
        # Here "参照: - 不明" parses as source=["不明"]. has_sources=True?
        # If "不明" is in sources, usually we don't treat it as valid source?
        # But parser just extracts lines. "不明" is a line. So sources=["不明"].
        # If has_sources=True, it hits Strong Check 1 (Positive Hallucination).
        
        # NOTE: S1 definition says "参照: 不明" is UNKNOWN_TOKEN. 
        # But mentions_unknown check handles input? 
        # mentions_unknown = "不明" in answer. => True.
        # If mentions_unknown is True -> determine_standard_fail_reason -> UNKNOWN_ANSWER.
        # apply_type_constraints(negative_control, UNKNOWN_ANSWER) -> PASS.
        
        # So ans_mixed passes UNKNOWN check.
        # But we want to fail on "unknown but..." (Mixed Hallucination).
        # apply_type_constraints has specific logic for "unknown but...":
        # The logic is:
        # if q_type == "negative_control":
        #    if fail_reason_code in (UNKNOWN...): return None (PASS)
        #    ...
        #    if fail_reason_code is None: ... check "however" ...
        
        # Wait, if it is UNKNOWN_ANSWER, it returns None (PASS) immediately!
        # My implementation of strict negative control check was:
        # "さらに結論行に ただし|しかし... が含まれる場合は 混ぜ物扱いで Fail"
        # This implies we should check "However" logic EVEN IF it is UNKNOWN_ANSWER?
        # Or does "However" check imply it was NOT caught as Unknown?
        
        # The requirement says:
        # "negative_control の Pass 条件：UNKNOWN... NO_SOURCES のいずれか"
        # "ただし sources が出ている（=参照ブロックに1件以上）場合は Fail"
        # "さらに結論行に ただし|しかし... が含まれる場合は 混ぜ物扱いで Fail"
        
        # So I need to modify apply_type_constraints to perform these checks *before* returning early for UNKNOWN?
        # Or do I consider "不明ですが..." as NOT UNKNOWN?
        # If "不明" is in conclusion, mentions_unknown=True. -> UNKNOWN_ANSWER.
        
        # Let's adjust apply_type_constraints in run_eval.py if needed, or adjust test expectation.
        # If the user says "Unknown but...", it is dangerous.
        # I should probably check for Hallucination indicators *before* allowing UNKNOWN pass?
        # Or maybe "Unknown but..." is caught by "mentions_unknown"? 
        # The user requirement: "negative_control で根拠があるのは “答えがある” 可能性が高い" -> Sources check overrides.
        
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.POSITIVE_HALLUCINATION)

if __name__ == '__main__':
    unittest.main()
