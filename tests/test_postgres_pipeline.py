import unittest

import pandas as pd

from src.config import DatabaseSettings, create_database_engine
from src.load_data import DECIMAL_COLUMNS, INTEGER_COLUMNS, _prepare_chunk


class PostgresPipelineTests(unittest.TestCase):
    def test_prepare_chunk_converts_nullable_numbers_and_dates(self):
        values = {column: ["1"] for column in INTEGER_COLUMNS}
        values.update({column: ["2"] for column in DECIMAL_COLUMNS})
        values["source_row_number"] = ["42"]
        values["unique_hhs"] = [None]
        values["trx_value_kes"] = ["123.45"]
        values["trx_date"] = ["2012-09-03"]

        prepared = _prepare_chunk(pd.DataFrame(values))

        self.assertEqual(prepared.loc[0, "source_row_number"], 42)
        self.assertTrue(pd.isna(prepared.loc[0, "unique_hhs"]))
        self.assertEqual(prepared.loc[0, "trx_value_kes"], 123.45)
        self.assertEqual(
            prepared.loc[0, "trx_date"],
            pd.Timestamp("2012-09-03"),
        )

    def test_database_url_escapes_special_password_characters(self):
        password = "safe:test@value/with?symbols"
        settings = DatabaseSettings(
            host="localhost",
            port=5432,
            database="kenya_cashflow_db",
            username="postgres",
            password=password,
        )
        engine = create_database_engine(settings)
        try:
            self.assertEqual(engine.url.password, password)
            self.assertNotIn(password, engine.url.render_as_string(hide_password=True))
            self.assertNotIn(password, repr(settings))
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
