import unittest
from eval.run_eval import analyze_result, ReasonCode

class TestEvalLogic(unittest.TestCase):

    def test_parse_sources_strict(self):
        # Case 1: Standard valid source
        q = {"id": "T01", "expected_source": "hello.md#chunk-0"}
        ans = "結論:\n- 答え\n\n根拠:\n- 答えと言える理由\n\n参照:\n- hello.md#chunk-0"
        res = analyze_result(q, ans, 0, "")
        self.assertTrue(res["passed"])
        self.assertIsNone(res["reason_code"])

        # Case 2: Source in text but not in reference block -> FAIL (NO_SOURCES)
        ans_fake = "参照: はありませんが hello.md#chunk-0 に書いてあります。"
        # This misses "結論:" block, so it hits FORMAT_INVALID first!
        res = analyze_result(q, ans_fake, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.FORMAT_INVALID)

        # Case 3: Partial match (file-level expectation vs chunk-level answer)
        q2 = {"id": "T02", "expected_source": "hello.md"}
        ans2 = "結論:\n- OK\n\n根拠:\n- OK\n\n参照:\n- hello.md#chunk-99"
        res = analyze_result(q2, ans2, 0, "")
        self.assertTrue(res["passed"])

    def test_format_invalid(self):
        # No conclusion block
        ans = "これは回答ですが、フォーマットに従っていません。"
        res = analyze_result({"id": "T99"}, ans, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.FORMAT_INVALID)

        # Conclusion block present but empty?
        ans_empty_list = "結論:\n\n参照:\n- s1" 
        res = analyze_result({"id": "T99"}, ans_empty_list, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.FORMAT_INVALID)

    def test_evidence_mode_any_vs_all(self):
        # Case 1: Normal (ANY) - 1 out of 3 is enough
        q_normal = {
            "id": "T11", 
            "type": "normal", 
            "expected_evidence": ["EvA", "EvB", "EvC"]
        }
        ans_partial = "結論:\n- ここに EvB があります。\n\n根拠:\n- EvB\n\n参照:\n- doc.md#chunk-1"
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
        ans_full = "結論:\n- EvAとEvBとEvCが揃っています。\n\n根拠:\n- EvAとEvBとEvC\n\n参照:\n- doc.md#chunk-1"
        res = analyze_result(q_bound, ans_full, 0, "")
        self.assertTrue(res["passed"])

    def test_unknown_detection_strict(self):
        # Case 1: Unknown in Conclusion -> FAIL (UNKNOWN_ANSWER)
        q = {"id": "T21", "type": "normal"}
        ans = "結論:\n- 不明です。\n\n参照:\n- 不明"
        res = analyze_result(q, ans, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.UNKNOWN_ANSWER)

        # Case 1b: "不確実な情報はありません" should NOT trigger Unknown
        ans_safe2 = "結論:\n- 答え。\n\n根拠:\n- 答え\n\n参照:\n- s1\n\n不確実性:\n- 不確実な情報はありません。"
        res = analyze_result(q, ans_safe2, 0, "")
        self.assertTrue(res["passed"])

        # Case 2: Unknown token in body text but Conclusion is fine -> PASS
        # We add '根拠' to avoid Mixed Hallucination on 'unknown', 'ペン', '英語'
        ans_safe = "結論:\n- これはペンです。\n\n根拠:\n- ペンです。英語ではunknownと言います。\n\n解説:\n- 英語ではunknownと言います。\n\n参照:\n- doc.md#chunk-1"
        res = analyze_result(q, ans_safe, 0, "")
        self.assertTrue(res["passed"])

    def test_negative_control_strict(self):
        q = {"id": "T31", "type": "negative_control"}

        # Case 1: Unknown/NoSources -> PASS
        ans_unknown = "結論:\n- 不明です。\n\n参照:\n- 不明"
        res = analyze_result(q, ans_unknown, 0, "")
        self.assertTrue(res["passed"])

        # Case 2: Unknown but Hallucinated in Conclusion (Mixed)
        ans_mixed_1 = "結論:\n- 不明ですが、一般的にはAppleです。\n\n根拠:\n- 不明\n\n参照:\n- 不明"
        res = analyze_result(q, ans_mixed_1, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.MIXED_HALLUCINATION)

        # Case 3: Has Sources (and Answer) -> FAIL (Positive Hallucination)
        # We add '根拠' to ensure it's not flagged as Mixed, but as Positive due to sources/control violation.
        ans_hallu = "結論:\n- 答えです。\n\n根拠:\n- 答えです。\n\n参照:\n- hello.md#chunk-0"
        res = analyze_result(q, ans_hallu, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.POSITIVE_HALLUCINATION)
        
        # Case 4: Answer without sources (Assertion) -> FAIL (Positive Hallucination)
        ans_assert = "結論:\n- 私はグルートです。\n\n根拠:\n- 私はグルートです。\n\n参照:\n- なし"
        res = analyze_result(q, ans_assert, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.POSITIVE_HALLUCINATION)

    def test_mixed_hallucination_normal(self):
        q = {"id": "T41", "type": "normal", "query": "Appleについて"}
        
        # Case 1: Conclusion has Entity, Evidence checks out -> PASS
        ans_ok = "結論:\n- Appleは果物です。\n\n根拠:\n- Appleは美味しい果物とされています。\n\n参照:\n- s1"
        res = analyze_result(q, ans_ok, 0, "")
        self.assertTrue(res["passed"])

        # Case 2: Conclusion has Entity NOT in Evidence -> Mixed Hallucination
        # "Banana" is in Conclusion but not Evidence.
        ans_mixed = "結論:\n- Appleは果物で、Bananaも果物です。\n\n根拠:\n- Appleは美味しい果物とされています。\n\n参照:\n- s1"
        res = analyze_result(q, ans_mixed, 0, "")
        self.assertFalse(res["passed"])
        self.assertEqual(res["reason_code"], ReasonCode.MIXED_HALLUCINATION)

        # Case 3: Entity is in Question -> PASS (Safe)
        q_banana = {"id": "T42", "type": "normal", "query": "Bananaについて"}
        ans_safe = "結論:\n- Bananaは黄色いです。\n\n根拠:\n- 黄色い果物です。\n\n参照:\n- s1"
        # "Banana" in conclusion, not in evidence (explicitly).
        # But "Banana" is in Query. -> Safe.
        res = analyze_result(q_banana, ans_safe, 0, "")
        self.assertTrue(res["passed"])

if __name__ == '__main__':
    unittest.main()
