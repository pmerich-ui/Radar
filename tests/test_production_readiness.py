import unittest
from src.production_readiness import readiness, require_readiness

class ProductionReadinessTests(unittest.TestCase):
    def test_empty_config_is_blocked(self):
        self.assertTrue(readiness({}))
        with self.assertRaises(RuntimeError):
            require_readiness({})
    def test_sqlite_is_blocked(self):
        env={"LEDGER_URL":"sqlite:///test.db","METRICOOL_BRAND_ID":"7820933","AWIN_PUBLISHER_ID":"3142204","PUBLISHING_ENABLED":"true"}
        self.assertIn("Production LEDGER_URL must use PostgreSQL",readiness(env))
    def test_known_configuration_passes_only_readiness(self):
        env={"LEDGER_URL":"postgresql://localhost/test","METRICOOL_BRAND_ID":"7820933","AWIN_PUBLISHER_ID":"3142204","PUBLISHING_ENABLED":"true"}
        self.assertEqual(readiness(env),[])

if __name__=="__main__":
    unittest.main()
