import logging
from contextlib import closing
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from runner.config.settings import acme_settings

logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(
        host=acme_settings.postgresql_host,
        port=acme_settings.postgresql_port,
        database=acme_settings.postgresql_database,
        user=acme_settings.postgresql_user,
        password=acme_settings.postgresql_password,
    )


def _serialise_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Converts datetime values into ISO strings so the result is easier
    for the agent/API layer to return as JSON.
    """
    if row is None:
        return None

    output = {}

    for key, value in row.items():
        if hasattr(value, "isoformat"):
            output[key] = value.isoformat()
        else:
            output[key] = value

    return output


def _serialise_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_serialise_row(row) for row in rows]


# ---------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------

def add_customer(
    name: str,
    industry: str | None = None,
    account_manager: str | None = None,
) -> int:
    """
    Create a customer.
    If the customer already exists, update their industry/account manager.
    Returns the customer_id.
    """
    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO customers (name, industry, account_manager)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name)
                    DO UPDATE SET
                        industry = EXCLUDED.industry,
                        account_manager = EXCLUDED.account_manager,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING customer_id;
                    """,
                    (name, industry, account_manager),
                )

                row = cur.fetchone()
                return row["customer_id"]


def get_customer(customer_name: str) -> dict[str, Any] | None:
    """
    Find one customer by exact name.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    customer_id,
                    name,
                    industry,
                    account_manager,
                    created_at,
                    updated_at
                FROM customers
                WHERE name = %s;
                """,
                (customer_name,),
            )

            return _serialise_row(cur.fetchone())


def get_customer_by_id(customer_id: int) -> dict[str, Any] | None:
    """
    Find one customer by customer_id.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    customer_id,
                    name,
                    industry,
                    account_manager,
                    created_at,
                    updated_at
                FROM customers
                WHERE customer_id = %s;
                """,
                (customer_id,),
            )

            return _serialise_row(cur.fetchone())


def list_customers(search: str | None = None) -> list[dict[str, Any]]:
    """
    List customers. Optionally search by name, industry, or account manager.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if search:
                cur.execute(
                    """
                    SELECT
                        customer_id,
                        name,
                        industry,
                        account_manager,
                        created_at,
                        updated_at
                    FROM customers
                    WHERE name ILIKE %s
                       OR industry ILIKE %s
                       OR account_manager ILIKE %s
                    ORDER BY name ASC;
                    """,
                    (f"%{search}%", f"%{search}%", f"%{search}%"),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        customer_id,
                        name,
                        industry,
                        account_manager,
                        created_at,
                        updated_at
                    FROM customers
                    ORDER BY name ASC;
                    """
                )

            return _serialise_rows(cur.fetchall())


def update_customer(
    customer_id: int,
    name: str | None = None,
    industry: str | None = None,
    account_manager: str | None = None,
) -> dict[str, Any] | None:
    """
    Update customer fields.
    Only supplied fields are updated.
    """
    updates = []
    values = []

    if name is not None:
        updates.append("name = %s")
        values.append(name)

    if industry is not None:
        updates.append("industry = %s")
        values.append(industry)

    if account_manager is not None:
        updates.append("account_manager = %s")
        values.append(account_manager)

    if not updates:
        return get_customer_by_id(customer_id)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(customer_id)

    sql = f"""
        UPDATE customers
        SET {", ".join(updates)}
        WHERE customer_id = %s
        RETURNING
            customer_id,
            name,
            industry,
            account_manager,
            created_at,
            updated_at;
    """

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                return _serialise_row(cur.fetchone())


# ---------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------

def add_issue(
    customer_id: int,
    title: str,
    status: str = "open",
    priority: str | None = None,
) -> int:
    """
    Create an issue linked to a customer.
    Returns the issue_id.

    Your current schema does not have an issues.name column,
    so this function does not accept or insert name.
    """
    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO issues (customer_id, title, status, priority)
                    VALUES (%s, %s, %s, %s)
                    RETURNING issue_id;
                    """,
                    (customer_id, title, status, priority),
                )

                row = cur.fetchone()
                return row["issue_id"]


def get_issue(issue_id: int) -> dict[str, Any] | None:
    """
    Find one issue by issue_id.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    i.issue_id,
                    i.customer_id,
                    c.name AS customer_name,
                    i.title,
                    i.status,
                    i.priority,
                    i.created_at,
                    i.updated_at
                FROM issues i
                JOIN customers c
                    ON c.customer_id = i.customer_id
                WHERE i.issue_id = %s;
                """,
                (issue_id,),
            )

            return _serialise_row(cur.fetchone())


def get_customer_issues(customer_id: int) -> list[dict[str, Any]]:
    """
    Get all issues for one customer.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    issue_id,
                    customer_id,
                    title,
                    status,
                    priority,
                    created_at,
                    updated_at
                FROM issues
                WHERE customer_id = %s
                ORDER BY created_at DESC;
                """,
                (customer_id,),
            )

            return _serialise_rows(cur.fetchall())


def get_customer_open_issues(customer_id: int) -> list[dict[str, Any]]:
    """
    Get all open/in-progress/blocked issues for one customer.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    issue_id,
                    customer_id,
                    title,
                    status,
                    priority,
                    created_at,
                    updated_at
                FROM issues
                WHERE customer_id = %s
                  AND status IN ('open', 'in_progress', 'blocked')
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    created_at DESC;
                """,
                (customer_id,),
            )

            return _serialise_rows(cur.fetchall())


def update_issue(
    issue_id: int,
    title: str | None = None,
    status: str | None = None,
    priority: str | None = None,
) -> dict[str, Any] | None:
    """
    Update an issue.
    """
    updates = []
    values = []

    if title is not None:
        updates.append("title = %s")
        values.append(title)

    if status is not None:
        updates.append("status = %s")
        values.append(status)

    if priority is not None:
        updates.append("priority = %s")
        values.append(priority)

    if not updates:
        return get_issue(issue_id)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(issue_id)

    sql = f"""
        UPDATE issues
        SET {", ".join(updates)}
        WHERE issue_id = %s
        RETURNING
            issue_id,
            customer_id,
            title,
            status,
            priority,
            created_at,
            updated_at;
    """

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                return _serialise_row(cur.fetchone())


# ---------------------------------------------------------------------
# Issue updates / notes
# ---------------------------------------------------------------------

def add_issue_update(issue_id: int, update_text: str) -> int:
    """
    Add a note/update to an issue.
    Returns the update_id.
    """
    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO issue_updates (issue_id, update_text)
                    VALUES (%s, %s)
                    RETURNING update_id;
                    """,
                    (issue_id, update_text),
                )

                row = cur.fetchone()
                return row["update_id"]


def get_issue_updates(issue_id: int) -> list[dict[str, Any]]:
    """
    Get all notes/updates for one issue.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    update_id,
                    issue_id,
                    update_text,
                    created_at,
                    updated_at
                FROM issue_updates
                WHERE issue_id = %s
                ORDER BY created_at DESC;
                """,
                (issue_id,),
            )

            return _serialise_rows(cur.fetchall())


def update_issue_update(
    update_id: int,
    update_text: str,
) -> dict[str, Any] | None:
    """
    Update an existing issue note.
    """
    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    UPDATE issue_updates
                    SET update_text = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE update_id = %s
                    RETURNING
                        update_id,
                        issue_id,
                        update_text,
                        created_at,
                        updated_at;
                    """,
                    (update_text, update_id),
                )

                return _serialise_row(cur.fetchone())


# ---------------------------------------------------------------------
# Next actions
# ---------------------------------------------------------------------

def add_next_action(
    issue_id: int,
    action_text: str,
    created_by: str | None = None,
) -> int:
    """
    Add a next action to an issue.
    Returns the action_id.
    """
    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO next_actions (issue_id, action_text, created_by)
                    VALUES (%s, %s, %s)
                    RETURNING action_id;
                    """,
                    (issue_id, action_text, created_by),
                )

                row = cur.fetchone()
                return row["action_id"]


def get_next_actions(issue_id: int) -> list[dict[str, Any]]:
    """
    Get all next actions for one issue.
    """
    with closing(get_connection()) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    action_id,
                    issue_id,
                    action_text,
                    created_by,
                    created_at,
                    updated_at
                FROM next_actions
                WHERE issue_id = %s
                ORDER BY created_at DESC;
                """,
                (issue_id,),
            )

            return _serialise_rows(cur.fetchall())


def update_next_action(
    action_id: int,
    action_text: str | None = None,
    created_by: str | None = None,
) -> dict[str, Any] | None:
    """
    Update a next action.
    """
    updates = []
    values = []

    if action_text is not None:
        updates.append("action_text = %s")
        values.append(action_text)

    if created_by is not None:
        updates.append("created_by = %s")
        values.append(created_by)

    if not updates:
        return None

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(action_id)

    sql = f"""
        UPDATE next_actions
        SET {", ".join(updates)}
        WHERE action_id = %s
        RETURNING
            action_id,
            issue_id,
            action_text,
            created_by,
            created_at,
            updated_at;
    """

    with closing(get_connection()) as conn:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                return _serialise_row(cur.fetchone())


# ---------------------------------------------------------------------
# Full customer overview for agent retrieval
# ---------------------------------------------------------------------

def get_customer_overview(customer_name: str) -> dict[str, Any] | None:
    """
    Get a customer, their issues, issue notes/updates, and next actions.

    This is the main read tool for the customer support agent.
    """
    customer = get_customer(customer_name)

    if customer is None:
        return None

    customer_id = customer["customer_id"]
    issues = get_customer_issues(customer_id)

    for issue in issues:
        issue_id = issue["issue_id"]
        issue["updates"] = get_issue_updates(issue_id)
        #issue["next_actions"] = get_next_actions(issue_id)

    customer["issues"] = issues

    return customer