import unittest
from unittest.mock import patch, AsyncMock
from pydantic import ValidationError
from app.schemas import GroundedAnswer
from app.services.generation import answer_with_sources

class StructuredTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_answer_and_schema_forwarding(self):
        with patch('app.services.generation.generate_answer',new_callable=AsyncMock,return_value='{"answer":"500 บาท","citation_ids":["chunk-2"]}') as model:
            answer=await answer_with_sources('เบิกเท่าไร',[{'id':'chunk-2','source':'demo.md','text':'500 บาท'}])
        self.assertEqual(answer.citation_ids,['chunk-2'])
        self.assertIn('output_schema',model.call_args.kwargs)
        schema = model.call_args.kwargs['output_schema']
        self.assertNotIn('found', schema['properties'])
        self.assertEqual(schema['properties']['citation_ids']['items']['enum'], ['chunk-2'])

    async def test_unknown_id_rejected(self):
        with patch('app.services.generation.generate_answer',new_callable=AsyncMock,return_value='{"answer":"500","citation_ids":["chunk-99"]}'):
            with self.assertRaises(ValueError):
                await answer_with_sources('test',[{'id':'chunk-2','source':'demo.md','text':'500'}])

    async def test_no_results_skips_model(self):
        with patch('app.services.generation.generate_answer',new_callable=AsyncMock) as model:
            answer=await answer_with_sources('test',[])
        self.assertFalse(answer.found)
        model.assert_not_awaited()

    def test_inconsistent_fields_rejected(self):
        for value in [
            {'answer':'500','citation_ids':[],'found':True},
            {'answer':'ไม่พบข้อมูลในเอกสาร','citation_ids':['chunk-1'],'found':False},
            {'answer':'เดา','citation_ids':[],'found':False},
            {'answer':'500','citation_ids':['chunk-1'],'found':'true'},
            {'answer':'500','citation_ids':['chunk-1'],'found':True,'extra':1},
        ]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError): GroundedAnswer.model_validate(value)
