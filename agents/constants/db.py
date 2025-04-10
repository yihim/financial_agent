DB_FILE = "transactions.db"

DB_TABLE_SCHEMA = """Table: transactions
Description: stores financial transaction records for clients across various banks and accounts.

client_id: 
    - INTEGER
    - Unique identifier for the client
bank_id:
    - INTEGER
    - Identifier for the bank
account_id:
    - INTEGER
    - Identifier for the specific account
transaction_id
    - INTEGER
    - Unique identifier for the transaction
transaction_date:
    - TIMESTAMP
    - Date and time when the transaction occurred
description:
    - TEXT (lower-cased)
    - Description of the transaction
category
    - TEXT (lower-cased)
    - Category of the transaction (e.g., shops, utilities, insurance, etc.)
merchant:
    - TEXT (lower-cased)
    - Name of the merchant/vendor
debit:
    - REAL
    - Amount debited
credit:
    - REAL
    - Amount credited"""
