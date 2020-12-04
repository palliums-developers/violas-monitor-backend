from bank.base import Base

create_table_sql = '''
    CREATE TABLE IF NOT EXISTS bank_monitor(
        key VARCHAR NOT NULL PRIMARY KEY,
        value jsonb
    );
'''

drop_table_sql = '''
    DROP TABLE bank_monitor
'''

def create_table():
    db_opt = Base()
    db_opt.execute(create_table_sql)

def drop_table():
    db_opt = Base()
    db_opt.execute(drop_table_sql)

if __name__ == "__main__":
    drop_table()
    create_table()

