import unittest
from unittest.mock import patch, AsyncMock
from experiments.evaluate_rag import evidence_coverage, evaluate_case
from app.schemas import GroundedAnswer

class EvaluationTests(unittest.IsolatedAsyncioTestCase):
    def test_quote_coverage_is_not_answer_accuracy(self):
        self.assertIsNone(evidence_coverage([], []))
        self.assertEqual(evidence_coverage(['500', 'receipt'], [{'text':'500 baht'}]), .5)

    async def test_false_abstention_is_recorded_not_passed(self):
        case={'id':'test','question':'limit?','language':'en','expected_found':True,'expected_answer':'500','evidence_quotes':['500']}
        chunks=[{'id':'chunk-1','text':'500','source':'demo.md','embedding':[1.,0.]}]
        answer=GroundedAnswer(answer='ไม่พบข้อมูลในเอกสาร', citation_ids=[], found=False)
        with patch('experiments.evaluate_rag.embed_texts',new_callable=AsyncMock,return_value=[[1.,0.]]), patch('experiments.evaluate_rag.answer_with_sources',new_callable=AsyncMock,return_value=answer):
            row=await evaluate_case(case,chunks,1)
        self.assertTrue(row['schema_and_ids_valid'])
        self.assertFalse(row['found_matches_expected'])
        self.assertEqual(row['exact_quote_coverage'],1)
        self.assertIsNone(row['manual_review']['answer_correct'])

    async def test_error_retains_retrieved_evidence(self):
        case={'id':'test','question':'limit?','language':'en','expected_found':True,'expected_answer':'500','evidence_quotes':['500']}
        chunks=[{'id':'chunk-1','text':'500','source':'demo.md','embedding':[1.,0.]}]
        with patch('experiments.evaluate_rag.embed_texts',new_callable=AsyncMock,return_value=[[1.,0.]]), patch('experiments.evaluate_rag.answer_with_sources',new_callable=AsyncMock,side_effect=ValueError('invalid answer')):
            row=await evaluate_case(case,chunks,1)
        self.assertFalse(row['schema_and_ids_valid'])
        self.assertEqual(row['error']['type'],'ValueError')
        self.assertEqual(len(row['retrieved']),1)
