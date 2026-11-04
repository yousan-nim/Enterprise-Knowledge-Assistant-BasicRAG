import unittest
from unittest.mock import patch

from psycopg.rows import dict_row

from app.storage import postgres


class PostgresConfigTests(unittest.TestCase):
    def test_environment_overrides_local_file(self):
        with patch.dict('os.environ', {'POSTGRES_PASSWORD': 'environment-password', 'POSTGRES_PORT': '5544'}, clear=True):
            with patch.object(postgres, 'dotenv_values', return_value={'POSTGRES_PASSWORD': 'file-password', 'POSTGRES_DB': 'file-db'}):
                with patch.object(postgres.psycopg, 'connect') as driver:
                    postgres.connect()
        driver.assert_called_once_with(
            host='127.0.0.1', port=5544, dbname='file-db', user='rag',
            password='environment-password', connect_timeout=10, row_factory=dict_row,
        )

    def test_missing_password_fails_before_connecting(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(postgres, 'dotenv_values', return_value={}):
                with patch.object(postgres.psycopg, 'connect') as driver:
                    with self.assertRaisesRegex(ValueError, 'POSTGRES_PASSWORD is required'):
                        postgres.connect()
        driver.assert_not_called()
