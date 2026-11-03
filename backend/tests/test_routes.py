import unittest
import httpx
from app.main import app

class VersionedRoutesTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_and_old_paths(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            response=await client.get('/api/v1/health')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json(),{'status':'ok'})
            for method,path in [('GET','/health'),('POST','/chat'),('POST','/documents'),('POST','/questions')]:
                with self.subTest(path=path):
                    self.assertEqual((await client.request(method,path)).status_code,404)

    async def test_swagger_describes_versioned_routes(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            docs=await client.get('/docs')
            self.assertEqual(docs.status_code,200)
            response=await client.get('/openapi.json')
        self.assertEqual(response.status_code,200)
        schema=response.json()
        self.assertEqual(set(schema['paths']),{'/api/v1/health','/api/v1/chat','/api/v1/documents','/api/v1/questions'})
        upload=schema['paths']['/api/v1/documents']['post']
        self.assertIn('multipart/form-data',upload['requestBody']['content'])
        question=schema['paths']['/api/v1/questions']['post']
        self.assertEqual(len(question['responses']['200']['content']['application/json']['examples']),2)
