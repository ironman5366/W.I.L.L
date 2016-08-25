#External imports
import dataset

#Internal imports
import log

#Connect to the W.I.L.L database
db = dataset.connect("sqlite://will.db")

def load_config(table, entry):
    log.info("In load_config with table {0} and entry{1}".format(table,entry))
    assert type(table) == str and type(entry) == str
    db_table = db[table]
    log.info("Loaded db table {0}".format(table))
    result_entry = db_table.find_one(name=entry)
    log.info("Found result entry {0}".format(result_entry))
    return result_entry
