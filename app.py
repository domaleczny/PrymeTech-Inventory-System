import os
import sqlite3
import tempfile
from flask import Flask, after_this_request, json, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename

import import_inventory

app = Flask(
    __name__,
    static_folder="images",
    static_url_path="/static/images",
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "inventory-secret-key")
DB_PATH = os.environ.get("INVENTORY_DB", import_inventory.DB_PATH)


def get_conn():
    return import_inventory.get_db_connection(DB_PATH)


def serialize_row(row):
    return {key: row[key] for key in row.keys()}


def parse_form_int(field_name, default=0):
    value = request.form.get(field_name)
    if value in (None, ""):
        return default
    return int(value)


@app.route("/")
def inventory_list():
    page = int(request.args.get("page", 1))
    per_page = 25
    low_stock = request.args.get("low_stock") == "1"
    location = request.args.get("location")
    customer = request.args.get("customer")
    search = request.args.get("search")

    conn = get_conn()
    rows = import_inventory.inventory_query(
        conn,
        low_stock=low_stock,
        location=location,
        customer=customer,
        search=search,
    )

    customer_rows = conn.execute("""
        SELECT DISTINCT customer
        FROM inventory
        WHERE customer IS NOT NULL
        AND customer != ''
        ORDER BY customer
    """).fetchall()

    customers = [row["customer"] for row in customer_rows]

    total = len(rows)
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(max(page, 1), pages)
    page_rows = rows[(page - 1) * per_page : page * per_page]

    return render_template(
        "inventory_list.html",
        items=[serialize_row(row) for row in page_rows],
        customers=customers,
        page=page,
        pages=pages,
        total=total,
        low_stock=low_stock,
        location=location or "",
        customer=customer or "",
        search=search or "",
    )

@app.route("/probe-inventory")
def probe_inventory_list():
    page = int(request.args.get("page", 1))
    per_page = 25
    low_stock = request.args.get("low_stock") == "1"
    location = request.args.get("location")
    customer = request.args.get("customer")
    search = request.args.get("search")

    conn = get_conn()
    rows = import_inventory.probe_inventory_query(
        conn,
        low_stock=low_stock,
        location=location,
        customer=customer,
        search=search,
    )

    customer_rows = conn.execute("""
        SELECT DISTINCT customer
        FROM probe_inventory
        WHERE customer IS NOT NULL
        AND customer != ''
        ORDER BY customer
    """).fetchall()

    customers = [row["customer"] for row in customer_rows]
    
    total = len(rows)
    pages = max((total + per_page - 1) // per_page, 1)
    page = min(max(page, 1), pages)
    page_rows = rows[(page - 1) * per_page : page * per_page]

    return render_template(
        "probe_inventory_list.html",
        items=[serialize_row(row) for row in page_rows],
        customers=customers,
        page=page,
        pages=pages,
        total=total,
        low_stock=low_stock,
        location=location or "",
        customer=customer or "",
        search=search or "",
    )


@app.route("/inventory/add", methods=["POST"])
def add_inventory_item():
    part_number = request.form.get("part_number", "").strip()
    if not part_number:
        flash("Part number is required.", "error")
        return redirect(url_for("inventory_list"))

    try:
        quantity = parse_form_int("quantity")
        min_quantity = parse_form_int("min_quantity")
    except ValueError:
        flash("Quantity and min quantity must be whole numbers.", "error")
        return redirect(url_for("inventory_list"))

    now = import_inventory.now_date()
    conn = get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO inventory (
                part_number, description, location, quantity,
                min_quantity, customer, last_modify_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                part_number,
                request.form.get("description") or None,
                request.form.get("location") or None,
                quantity,
                min_quantity,
                request.form.get("customer") or None,
                now,
            ),
        )
    except sqlite3.IntegrityError:
        flash("An item with that part number already exists.", "error")
        return redirect(url_for("inventory_list"))

    import_inventory.record_change(conn, part_number, "create", {
        "part_number": {"old": None, "new": part_number},
        "description": {"old": None, "new": request.form.get("description") or None},
        "location": {"old": None, "new": request.form.get("location") or None},
        "quantity": {"old": None, "new": quantity},
        "min_quantity": {"old": None, "new": min_quantity},
        "customer": {"old": None, "new": request.form.get("customer") or None},
    }, changed_by="web")
    flash("Item added successfully.", "success")
    return redirect(url_for("item_detail", item_id=cursor.lastrowid))


@app.route("/probe-inventory/add", methods=["POST"])
def add_probe_inventory_item():
    part_number = request.form.get("part_number", "").strip()
    if not part_number:
        flash("Part number is required.", "error")
        return redirect(url_for("probe_inventory_list"))

    try:
        quantity = parse_form_int("quantity")
        min_quantity = parse_form_int("min_quantity")
    except ValueError:
        flash("Quantity and min quantity must be whole numbers.", "error")
        return redirect(url_for("probe_inventory_list"))

    now = import_inventory.now_date()
    fields = {
        "part_number": part_number,
        "description": request.form.get("description") or None,
        "location": request.form.get("location") or None,
        "quantity": quantity,
        "min_quantity": min_quantity,
        "customer": request.form.get("customer") or None,
        "thread_size": request.form.get("thread_size") or None,
        "sphere_dk": request.form.get("sphere_dk") or None,
        "length": request.form.get("length") or None,
        "ml_ewl": request.form.get("ml_ewl") or None,
        "tip_material": request.form.get("tip_material") or None,
        "shaft_material": request.form.get("shaft_material") or None,
        "probe_type": request.form.get("probe_type") or None,
        "link": request.form.get("link") or None,
    }

    conn = get_conn()
    try:
        cursor = conn.execute(
            """INSERT INTO probe_inventory (
                part_number, description, location, quantity, min_quantity, customer,
                last_modify_date, thread_size, sphere_dk, length, ml_ewl,
                tip_material, shaft_material, probe_type, link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fields["part_number"], fields["description"], fields["location"],
                fields["quantity"], fields["min_quantity"], fields["customer"], now,
                fields["thread_size"], fields["sphere_dk"], fields["length"],
                fields["ml_ewl"], fields["tip_material"], fields["shaft_material"],
                fields["probe_type"], fields["link"],
            ),
        )
    except sqlite3.IntegrityError:
        flash("An item with that part number already exists.", "error")
        return redirect(url_for("probe_inventory_list"))

    import_inventory.record_change(
        conn,
        part_number,
        "create",
        {field: {"old": None, "new": value} for field, value in fields.items()},
        changed_by="web",
    )
    flash("Probe item added successfully.", "success")
    return redirect(url_for("probe_item_detail", item_id=cursor.lastrowid))

@app.route("/probe-inventory/<int:item_id>", methods=["GET", "POST"])
def probe_item_detail(item_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM probe_inventory WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        flash("Item not found.", "error")
        return redirect(url_for("probe_inventory_list"))

    item = serialize_row(row)
    if request.method == "POST":
        original_timestamp = request.form.get("last_modify_date")
        if original_timestamp != item["last_modify_date"]:
            flash("This item was modified by another process. Reload to continue.", "warning")
            return redirect(url_for("probe_item_detail", item_id=item_id))

        updated = {
            "description": request.form.get("description") or None,
            "location": request.form.get("location") or None,
            "quantity": int(request.form.get("quantity", item["quantity"])),
            "min_quantity": int(request.form.get("min_quantity", item["min_quantity"])),
            "customer": request.form.get("customer") or None,
            "thread_size": request.form.get("thread_size") or None,
            "sphere_dk": request.form.get("sphere_dk") or None,
            "length": request.form.get("length") or None,
            "ml_ewl": request.form.get("ml_ewl") or None,
            "tip_material": request.form.get("tip_material") or None,
            "shaft_material": request.form.get("shaft_material") or None,
            "probe_type": request.form.get("probe_type") or None,
            "link": request.form.get("link") or None,
        }
        changed = {}
        for field, value in updated.items():
            if item[field] != value:
                changed[field] = {"old": item[field], "new": value}

        if changed:
            now = import_inventory.now_date()
            conn.execute(
                """UPDATE probe_inventory SET
                    description = ?, location = ?, quantity = ?, min_quantity = ?, customer = ?,
                    thread_size = ?, sphere_dk = ?, length = ?, ml_ewl = ?,
                    tip_material = ?, shaft_material = ?, probe_type = ?, link = ?,
                    last_modify_date = ?
                WHERE id = ?""",
                (
                    updated["description"], updated["location"],
                    updated["quantity"], updated["min_quantity"], updated["customer"],
                    updated["thread_size"], updated["sphere_dk"], updated["length"],
                    updated["ml_ewl"], updated["tip_material"], updated["shaft_material"],
                    updated["probe_type"], updated["link"],
                    now, item_id,
                ),
            )
            import_inventory.record_change(conn, item["part_number"], "update", changed, changed_by="web")
            flash("Item updated successfully.", "success")
            return redirect(url_for("probe_item_detail", item_id=item_id))

        flash("No changes were detected.", "info")

    return render_template("probe_item_detail.html", item=item)

@app.route("/dashboard")
def dashboard():
    conn = get_conn()
    low_stock_items = import_inventory.inventory_query(conn, low_stock=True)
    total_items = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]

    recent_changes = []
    for row in conn.execute("SELECT * FROM changes ORDER BY timestamp DESC LIMIT 20").fetchall():
        change = serialize_row(row)
        try:
            change["diff"] = json.loads(change["diff"])
        except (ValueError, TypeError):
            change["diff"] = {}
        recent_changes.append(change)

    low_stock_items_sorted = sorted(
        [serialize_row(row) for row in low_stock_items[:10]],
        key=lambda item: (item["quantity"] / item["min_quantity"])
        if item["min_quantity"] else float("inf")
    )

    return render_template(
        "dashboard.html",
        total_items=total_items,
        low_stock_count=len(low_stock_items),
        low_stock_items=low_stock_items_sorted,
        recent_changes=recent_changes,
    )

@app.route("/api/locations", methods=["GET"])
def api_locations_list():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM inventory_locations ORDER BY id").fetchall()
    return jsonify([serialize_row(row) for row in rows])


@app.route("/api/locations/<int:location_id>", methods=["PUT"])
def api_location_update(location_id):
    data = request.get_json(force=True)
    allowed = {"location_code", "description", "last_updated"}
    update_values = {key: data[key] for key in allowed if key in data}
    if not update_values:
        return jsonify({"error": "No valid fields provided"}), 400

    conn = get_conn()
    row = conn.execute("SELECT * FROM inventory_locations WHERE id = ?", (location_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Not found"}), 404

    conn.execute(
        "UPDATE inventory_locations SET location_code = ?, description = ?, last_updated = ? WHERE id = ?",
        (
            update_values.get("location_code", row["location_code"]),
            update_values.get("description", row["description"]),
            update_values.get("last_updated", row["last_updated"]),
            location_id,
        ),
    )
    return jsonify({"updated": True})

@app.route("/<int:item_id>/remove", methods=["GET", "POST"])
def remove_inventory_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT part_number FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        flash("Item not found.", "error")
        return redirect(url_for("inventory_list"))

    conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
    import_inventory.record_change(conn, row["part_number"], "delete", {}, changed_by="web")
    flash("Item removed successfully.", "success")
    return redirect(url_for("inventory_list"))


@app.route("/probe-inventory/<int:item_id>/remove", methods=["GET", "POST"])
def remove_probe_inventory_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT part_number FROM probe_inventory WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        flash("Item not found.", "error")
        return redirect(url_for("probe_inventory_list"))

    conn.execute("DELETE FROM probe_inventory WHERE id = ?", (item_id,))
    import_inventory.record_change(conn, row["part_number"], "delete", {}, changed_by="web")
    flash("Probe item removed successfully.", "success")
    return redirect(url_for("probe_inventory_list"))


@app.route("/<int:item_id>", methods=["GET", "POST"])
def item_detail(item_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        flash("Item not found.", "error")
        return redirect(url_for("inventory_list"))

    item = serialize_row(row)
    if request.method == "POST":
        original_timestamp = request.form.get("last_modify_date")
        if original_timestamp != item["last_modify_date"]:
            flash("This item was modified by another process. Reload to continue.", "warning")
            return redirect(url_for("item_detail", item_id=item_id))

        updated = {
            "description": request.form.get("description") or None,
            "location": request.form.get("location") or None,
            "quantity": int(request.form.get("quantity", item["quantity"])),
            "min_quantity": int(request.form.get("min_quantity", item["min_quantity"])),
            "customer": request.form.get("customer") or None,
        }
        changed = {}
        for field, value in updated.items():
            if item[field] != value:
                changed[field] = {"old": item[field], "new": value}

        if changed:
            now = import_inventory.now_date()
            conn.execute(
                "UPDATE inventory SET description = ?, location = ?, quantity = ?, min_quantity = ?, customer = ?, last_modify_date = ? WHERE id = ?",
                (
                    updated["description"],
                    updated["location"],
                    updated["quantity"],
                    updated["min_quantity"],
                    updated["customer"],
                    now,
                    item_id,
                ),
            )
            import_inventory.record_change(conn, item["part_number"], "update", changed, changed_by="web")
            flash("Item updated successfully.", "success")
            return redirect(url_for("item_detail", item_id=item_id))

        flash("No changes were detected.", "info")

    return render_template("item_detail.html", item=item)


@app.route("/import", methods=["GET", "POST"])
def import_page():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        if uploaded_file is None or uploaded_file.filename == "":
            flash("Please select an Excel file to upload.", "error")
            return redirect(url_for("import_page"))

        filename = secure_filename(uploaded_file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        uploaded_file.save(temp_path)

        try:
            summary = import_inventory.import_excel(temp_path, db_path=DB_PATH, changed_by="web")
            flash(
                f"Import completed: inserted={summary['inserted']} updated={summary['updated']} skipped={summary['skipped']} invalid={len(summary['invalid_rows'])}",
                "success",
            )
        except Exception as exc:
            flash(f"Import failed: {exc}", "error")
        return redirect(url_for("import_page"))

    return render_template("import.html")


@app.route("/probe-import", methods=["GET", "POST"])
def probe_import_page():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        if uploaded_file is None or uploaded_file.filename == "":
            flash("Please select an Excel file to upload.", "error")
            return redirect(url_for("probe_import_page"))

        filename = secure_filename(uploaded_file.filename)
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, filename)
        uploaded_file.save(temp_path)

        try:
            summary = import_inventory.import_probe_excel(temp_path, db_path=DB_PATH, changed_by="web")
            flash(
                f"Import completed: inserted={summary['inserted']} updated={summary['updated']} skipped={summary['skipped']} invalid={len(summary['invalid_rows'])}",
                "success",
            )
        except Exception as exc:
            flash(f"Import failed: {exc}", "error")
        return redirect(url_for("probe_import_page"))

    return render_template("probe_import.html")


@app.route("/export")
def export_page():
    fmt = request.args.get("format", "csv").lower()
    low_stock = request.args.get("low_stock") == "1"
    location = request.args.get("location")
    customer = request.args.get("customer")
    search = request.args.get("search")

    conn = get_conn()
    rows = import_inventory.inventory_query(
        conn,
        low_stock=low_stock,
        location=location,
        customer=customer,
        search=search,
    )
    suffix = ".xlsx" if fmt == "xlsx" else ".csv"
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.close()
    import_inventory.export_rows(rows, temp_file.name, fmt=fmt)

    @after_this_request
    def cleanup(response):
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass
        return response

    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f"inventory_export{suffix}",
    )


@app.route("/api/inventory", methods=["GET"])
def api_inventory_list():
    conn = get_conn()
    rows = import_inventory.inventory_query(conn,
        low_stock=request.args.get("low_stock") == "1",
        location=request.args.get("location"),
        customer=request.args.get("customer"),
        search=request.args.get("search"),
    )
    return jsonify([serialize_row(row) for row in rows])


@app.route("/api/inventory/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def api_inventory_item(item_id):
    conn = get_conn()
    if request.method == "GET":
        row = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(serialize_row(row))

    if request.method == "DELETE":
        row = conn.execute("SELECT part_number FROM inventory WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        import_inventory.record_change(conn, row["part_number"], "delete", {}, changed_by="web")
        return jsonify({"deleted": True})

    data = request.get_json(force=True)
    allowed = {"description", "location", "quantity", "min_quantity", "customer"}
    update_values = {key: data[key] for key in allowed if key in data}
    if not update_values:
        return jsonify({"error": "No valid fields provided"}), 400

    row = conn.execute("SELECT * FROM inventory WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Not found"}), 404

    changed = {}
    for field, new_value in update_values.items():
        existing_value = row[field]
        if field in {"quantity", "min_quantity"}:
            new_value = int(new_value)
        if existing_value != new_value:
            changed[field] = {"old": existing_value, "new": new_value}

    if changed:
        now = import_inventory.now_date()
        conn.execute(
            "UPDATE inventory SET description = ?, location = ?, quantity = ?, min_quantity = ?, customer = ?, last_modify_date = ? WHERE id = ?",
            (
                update_values.get("description", row["description"]),
                update_values.get("location", row["location"]),
                update_values.get("quantity", row["quantity"]),
                update_values.get("min_quantity", row["min_quantity"]),
                update_values.get("customer", row["customer"]),
                now,
                item_id,
            ),
        )
        import_inventory.record_change(conn, row["part_number"], "update", changed, changed_by="web")

    return jsonify({"updated": True})

@app.route("/api/probe-inventory", methods=["GET"])
def api_probe_inventory_list():
    conn = get_conn()
    rows = import_inventory.probe_inventory_query(conn,
        low_stock=request.args.get("low_stock") == "1",
        location=request.args.get("location"),
        customer=request.args.get("customer"),
        search=request.args.get("search"),
    )
    return jsonify([serialize_row(row) for row in rows])


@app.route("/api/probe-inventory/<int:item_id>", methods=["GET", "PUT", "DELETE"])
def api_probe_inventory_item(item_id):
    conn = get_conn()
    if request.method == "GET":
        row = conn.execute("SELECT * FROM probe_inventory WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(serialize_row(row))

    if request.method == "DELETE":
        row = conn.execute("SELECT part_number FROM probe_inventory WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        conn.execute("DELETE FROM probe_inventory WHERE id = ?", (item_id,))
        import_inventory.record_change(conn, row["part_number"], "delete", {}, changed_by="web")
        return jsonify({"deleted": True})

    data = request.get_json(force=True)
    allowed = {
        "description", "location", "quantity", "min_quantity", "customer",
        "thread_size", "sphere_dk", "length", "ml_ewl",
        "tip_material", "shaft_material", "probe_type", "link"
    }
    update_values = {key: data[key] for key in allowed if key in data}
    if not update_values:
        return jsonify({"error": "No valid fields provided"}), 400

    row = conn.execute("SELECT * FROM probe_inventory WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        return jsonify({"error": "Not found"}), 404

    changed = {}
    for field, new_value in update_values.items():
        existing_value = row[field]
        if field in {"quantity", "min_quantity"}:
            new_value = int(new_value)
        if existing_value != new_value:
            changed[field] = {"old": existing_value, "new": new_value}

    if changed:
        now = import_inventory.now_date()
        conn.execute(
            """UPDATE probe_inventory SET
                description = ?, location = ?, quantity = ?, min_quantity = ?, customer = ?,
                thread_size = ?, sphere_dk = ?, length = ?, ml_ewl = ?,
                tip_material = ?, shaft_material = ?, probe_type = ?, link = ?,
                last_modify_date = ?
            WHERE id = ?""",
            (
                update_values.get("description", row["description"]),
                update_values.get("location", row["location"]),
                update_values.get("quantity", row["quantity"]),
                update_values.get("min_quantity", row["min_quantity"]),
                update_values.get("customer", row["customer"]),
                update_values.get("thread_size", row["thread_size"]),
                update_values.get("sphere_dk", row["sphere_dk"]),
                update_values.get("length", row["length"]),
                update_values.get("ml_ewl", row["ml_ewl"]),
                update_values.get("tip_material", row["tip_material"]),
                update_values.get("shaft_material", row["shaft_material"]),
                update_values.get("probe_type", row["probe_type"]),
                update_values.get("link", row["link"]),
                now,
                item_id,
            ),
        )
        import_inventory.record_change(conn, row["part_number"], "update", changed, changed_by="web")

    return jsonify({"updated": True})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
