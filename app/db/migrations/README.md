# Database Migrations

This directory contains the migration files for the database schema changes. 

## Usage

To apply migrations, use the following command:

```
alembic upgrade head
```

To create a new migration, use:

```
alembic revision --autogenerate -m "Your migration message"
```

## Notes

- Ensure that your database connection is properly configured in the `app/db/database.py` file.
- Always review the generated migration files before applying them to ensure they meet your expectations.