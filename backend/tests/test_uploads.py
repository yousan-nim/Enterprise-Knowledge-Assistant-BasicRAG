import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
import httpx
from app.main import app, MAX_UPLOAD_BYTES
from app.storage.sqlite import get_chunks, replace_chunks

class UploadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.setup_database()
        self.old=[{'id':'old','document_id':'old-doc','text':'old','source':'old.md','embedding':[1.,0.]}]
        replace_chunks(self.old)
    def setup_database(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch('app.storage.sqlite.DATA_DIR', Path(directory.name))
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self): pass

    async def test_indexes_uploaded_text_not_sample(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts',new_callable=AsyncMock,return_value=[[1.,0.]]) as embed:
                r=await client.post('/documents',files={'file':('custom.md','ข้อมูลใหม่สำหรับทดสอบ'.encode(),'text/markdown')})
        self.assertEqual(r.status_code,201)
        embed.assert_awaited_once_with(['ข้อมูลใหม่สำหรับทดสอบ'])
        self.assertEqual(get_chunks()[0]['source'],'custom.md')

    async def test_invalid_upload_keeps_previous_document(self):
        cases=[('file.pdf',b'PDF',415),('empty.txt',b'   ',422),('bad.txt',b'\xff',422),('null.txt',b'a\x00b',422),('large.txt',b'a'*(MAX_UPLOAD_BYTES+1),413),('long.md',b'a'*50001,413)]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts',new_callable=AsyncMock) as embed:
                for name,data,status in cases:
                    with self.subTest(name=name):
                        r=await client.post('/documents',files={'file':(name,data)})
                        self.assertEqual(r.status_code,status)
                        self.assertEqual(get_chunks(),self.old)
                embed.assert_not_awaited()

    async def test_normalizes_name_and_accepts_utf8_bom(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            with patch('app.services.ingestion.embed_texts',new_callable=AsyncMock,return_value=[[1.,0.]]) as embed:
                r=await client.post('/documents',files={'file':('../name.MD',b'\xef\xbb\xbfhello')})
        self.assertEqual(r.status_code,201)
        self.assertEqual(r.json()['source'],'name.MD')
        embed.assert_awaited_once_with(['hello'])
