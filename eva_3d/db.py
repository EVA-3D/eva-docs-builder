import sqlite3
from sqlite3 import Error


def get_db_connection():
    conn = None
    try:
        conn = sqlite3.connect(":memory:")
        # conn = sqlite3.connect('db.sqlite3')
        print(sqlite3.version)
        return conn
    except Error as e:
        print(e)


def initialize_db(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bom (
            id INTEGER PRIMARY KEY,
            file_path TEXT,
            namespace TEXT
        );
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS item_entry (
            id INTEGER PRIMARY KEY,
            name TEXT,
            qty INTEGER,
            type TEXT,
            url TEXT,
            bom_id INTEGER,
            FOREIGN KEY (bom_id) REFERENCES bom (id)
        );
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vendor_mapping (
            id INTEGER PRIMARY KEY,
            vendor_name TEXT,
            eva_part_name TEXT,
            eva_part_type TEXT,
            vendor_part_name TEXT,
            vendor_sku TEXT,
            vendor_ignore INTEGER,
            FOREIGN KEY (eva_part_name) REFERENCES item_entry (name)
        );
    """
    )


def create_bom(conn, file_path, namespace):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO bom (
            file_path,
            namespace
        ) VALUES (?,?)
    """,
        (file_path, namespace),
    )
    conn.commit()
    return cur.lastrowid


def create_item_entry(conn, bom_id, name, qty, type, url):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO item_entry (
            bom_id,
            name,
            qty,
            type,
            url
        ) VALUES (?,?,?,?,?)
    """,
        (bom_id, name, qty, type, url),
    )
    conn.commit()
    return cur.lastrowid


def get_items_by_bom_id(conn, bom_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            name,
            SUM(qty) qty,
            type,
            url
        FROM item_entry 
        WHERE bom_id = ?
        GROUP BY name
    """,
        (bom_id,),
    )
    return cur.fetchall()


def create_vendor_mapping(
    conn,
    vendor_name,
    eva_part_name,
    eva_part_type,
    vendor_part_name,
    vendor_sku,
    vendor_ignore,
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO vendor_mapping (
            vendor_name,
            eva_part_name,
            eva_part_type,
            vendor_part_name,
            vendor_sku,
            vendor_ignore
        ) VALUES (?,?,?,?,?,?)
    """,
        (
            vendor_name,
            eva_part_name,
            eva_part_type,
            vendor_part_name,
            vendor_sku,
            1 if vendor_ignore else 0,
        ),
    )
    conn.commit()
    return cur.lastrowid


def truncate_vendor_mapping(conn):
    cur = conn.cursor()
    cur.execute("""DELETE FROM vendor_mapping""")
    conn.commit()


def get_vendors(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT vendor_name
        FROM vendor_mapping 
        GROUP BY vendor_name
    """,
    )
    return cur.fetchall()


def get_superbom(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            namespace,
            name,
            SUM(qty) qty,
            type,
            url
        FROM item_entry 
        INNER JOIN bom ON bom.id = item_entry.bom_id
        GROUP BY namespace, name
    """,
    )
    return cur.fetchall()


def get_vendor_superbom(conn, vendor_name):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            sub.name,
            SUM(sub.qty) qty,
            sub.type,
            sub.vendor_part_name,
            sub.vendor_sku
        FROM (
            SELECT 
                namespace,
                name,
                MAX(qty) qty,
                type,
                vendor_part_name,
                vendor_sku
            FROM item_entry 
            INNER JOIN bom ON bom.id = item_entry.bom_id
            LEFT JOIN vendor_mapping ON vendor_mapping.eva_part_name = item_entry.name
            WHERE vendor_name = ? AND vendor_ignore = 0
            GROUP BY namespace, name
        ) AS sub
        WHERE sub.type = "hardware"
        GROUP BY name
    """,
        (vendor_name,),
    )
    return cur.fetchall()
