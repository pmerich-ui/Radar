import unittest
from src.sqlite_readiness import sqlite_readiness

class SqliteReadinessTests(unittest.TestCase):
    def test_missing_mount_blocks(self):
        self.assertTrue(sqlite_readiness({}))
    def test_ephemeral_location_blocks(self):
        self.assertTrue(sqlite_readiness({"LEDGER_SQLITE_PATH":"/tmp/ledger.db","LEDGER_PERSISTENT_DIR":"/data","LEDGER_SINGLE_WRITER":"true","LEDGER_BACKUP_ENABLED":"true"}))
    def test_single_writer_and_backup_required(self):
        self.assertTrue(sqlite_readiness({"LEDGER_SQLITE_PATH":"/data/ledger.db","LEDGER_PERSISTENT_DIR":"/data"}))
    def test_valid_configuration_has_no_config_errors(self):
        self.assertEqual(sqlite_readiness({"LEDGER_SQLITE_PATH":"/data/ledger.db","LEDGER_PERSISTENT_DIR":"/data","LEDGER_SINGLE_WRITER":"true","LEDGER_BACKUP_ENABLED":"true"}),[])

if __name__=="__main__":
    unittest.main()
