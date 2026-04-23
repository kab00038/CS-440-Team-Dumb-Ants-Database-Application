from datetime import date
import ipaddress
import random
import re
from typing import Callable

import streamlit as st

from db import connect_to_database, run_query

STATUS_OPTIONS = ["active", "maintenance", "retired"]
DEVICE_CLASS_OPTIONS = ["Server", "Workstation", "Network Device"]
DEVICE_PREFIX_MAP = {
    "Server": "SRV",
    "Workstation": "WS",
    "Network Device": "ND",
}
HOSTNAME_TYPE_MAP = {
    "Server": "SRV",
    "Workstation": "WS",
    "Network Device": "NDV",
}

SERVER_RACK_UNITS = ["1U", "2U", "4U", "Blade"]
SERVER_CPU_OPTIONS = [2, 4, 8, 16, 24, 32, 64]
SERVER_RAM_OPTIONS = [8, 16, 32, 64, 128, 256, 512]
WORKSTATION_FORM_FACTORS = ["Desktop", "Laptop", "Thin Client"]
NETWORK_DEVICE_TYPES = ["Access Point", "Firewall", "Router", "Switch"]
NETWORK_PORT_OPTIONS = [0, 4, 8, 16, 24, 48]

ROOM_NUMBER_PATTERN = re.compile(r"^\d{3}([A-Za-z])?$")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@mix\.wvu\.edu$", re.IGNORECASE)


def _location_abbrev(location_id: str) -> str:
    return str(location_id).split("-")[0].upper()


def _normalize_room_number(room_number: str) -> str:
    return room_number.strip().upper()


def _is_valid_room_number(room_number: str) -> bool:
    # Enforce 3 digits with optional trailing letter (for example, 302 or 302B).
    return bool(ROOM_NUMBER_PATTERN.fullmatch(_normalize_room_number(room_number)))


def _is_valid_email(email_value: str) -> bool:
    value = email_value.strip().lower()
    return len(value) <= 254 and bool(EMAIL_PATTERN.fullmatch(value))


def _resolve_location_id(locations: list[dict], building_name: str, room_number: str) -> str | None:
    normalized_room = _normalize_room_number(room_number)
    for location in locations:
        if location["building_name"] == building_name and str(location["room_number"]).upper() == normalized_room:
            return location["location_id"]
    return None


def _location_prefix_for_building(locations: list[dict], building_name: str) -> str | None:
    for location in locations:
        if location["building_name"] == building_name:
            return _location_abbrev(location["location_id"])
    return None


def _resolve_or_build_location_id(locations: list[dict], building_name: str, room_number: str) -> str | None:
    existing_location_id = _resolve_location_id(locations, building_name, room_number)
    if existing_location_id:
        return existing_location_id

    prefix = _location_prefix_for_building(locations, building_name)
    if not prefix:
        return None

    normalized_room = _normalize_room_number(room_number)
    return f"{prefix}-{normalized_room}"


def _ensure_location_exists(connection, locations: list[dict], building_name: str, room_number: str) -> str:
    existing_location_id = _resolve_location_id(locations, building_name, room_number)
    if existing_location_id:
        return existing_location_id

    prefix = _location_prefix_for_building(locations, building_name)
    if not prefix:
        raise ValueError("No location prefix found for selected building")

    normalized_room = _normalize_room_number(room_number)
    new_location_id = f"{prefix}-{normalized_room}"

    existing_rows = run_query(
        connection,
        "SELECT location_id FROM location WHERE location_id = %s",
        (new_location_id,),
    )
    if existing_rows:
        return new_location_id

    template = next((row for row in locations if row["building_name"] == building_name), None)
    if not template:
        raise ValueError("No location template found for selected building")

    run_query(
        connection,
        """
        INSERT INTO location (location_id, building_name, room_number, rack_capacity, has_cooling, security_level)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            new_location_id,
            building_name,
            normalized_room,
            template["rack_capacity"],
            template["has_cooling"],
            template["security_level"],
        ),
        commit=False,
    )

    locations.append(
        {
            "location_id": new_location_id,
            "building_name": building_name,
            "room_number": normalized_room,
            "rack_capacity": template["rack_capacity"],
            "has_cooling": template["has_cooling"],
            "security_level": template["security_level"],
        }
    )
    return new_location_id


def _add_years(base_date: date, years: int) -> date:
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handle leap day by snapping to Feb 28 on non-leap years.
        return base_date.replace(month=2, day=28, year=base_date.year + years)


def _generate_asset_id(connection, device_class: str, location_id: str, exclude_asset_id: str | None = None) -> str:
    prefix = DEVICE_PREFIX_MAP[device_class]
    loc = _location_abbrev(location_id)
    like_pattern = f"{prefix}-{loc}-%"

    rows = run_query(
        connection,
        "SELECT asset_id FROM managed_assets WHERE asset_id LIKE %s",
        (like_pattern,),
    )

    max_seq = 0
    for row in rows:
        value = row.get("asset_id")
        if not value or value == exclude_asset_id:
            continue
        parts = str(value).split("-")
        if len(parts) >= 3 and parts[0] == prefix and parts[1] == loc and parts[-1].isdigit():
            max_seq = max(max_seq, int(parts[-1]))

    return f"{prefix}-{loc}-{max_seq + 1:02d}"


def _generate_hostname(connection, device_class: str, location_id: str, exclude_asset_id: str | None = None) -> str:
    loc = _location_abbrev(location_id)
    type_code = HOSTNAME_TYPE_MAP[device_class]
    like_pattern = f"{loc}-{type_code}-%"

    rows = run_query(
        connection,
        "SELECT asset_id, hostname FROM managed_assets WHERE hostname LIKE %s",
        (like_pattern,),
    )

    max_seq = 0
    for row in rows:
        if row.get("asset_id") == exclude_asset_id:
            continue
        hostname = row.get("hostname")
        if not hostname:
            continue
        parts = str(hostname).split("-")
        if len(parts) >= 3 and parts[0] == loc and parts[1] == type_code and parts[-1].isdigit():
            max_seq = max(max_seq, int(parts[-1]))

    return f"{loc}-{type_code}-{max_seq + 1:02d}"


def _generate_ip_address(connection, location_id: str, exclude_asset_id: str | None = None) -> str:
    rows = run_query(
        connection,
        "SELECT asset_id, ip_address FROM managed_assets WHERE location_id = %s",
        (location_id,),
    )

    subnet_counts: dict[tuple[int, int, int], int] = {}
    used_hosts: dict[tuple[int, int, int], set[int]] = {}

    for row in rows:
        if row.get("asset_id") == exclude_asset_id:
            continue
        ip_value = row.get("ip_address")
        if not ip_value:
            continue
        try:
            parsed_ip = ipaddress.ip_address(str(ip_value))
            if parsed_ip.version != 4:
                continue
        except ValueError:
            continue

        octets = str(parsed_ip).split(".")
        subnet = (int(octets[0]), int(octets[1]), int(octets[2]))
        host = int(octets[3])
        subnet_counts[subnet] = subnet_counts.get(subnet, 0) + 1
        if subnet not in used_hosts:
            used_hosts[subnet] = set()
        used_hosts[subnet].add(host)

    if subnet_counts:
        base_subnet = max(subnet_counts, key=subnet_counts.get)
    else:
        seed = sum(ord(c) for c in str(location_id))
        base_subnet = (10, 20 + (seed % 200), 10 + ((seed * 3) % 200))

    current_hosts = used_hosts.get(base_subnet, set())
    for host in range(10, 255):
        if host not in current_hosts:
            return f"{base_subnet[0]}.{base_subnet[1]}.{base_subnet[2]}.{host}"

    return f"{base_subnet[0]}.{base_subnet[1]}.{base_subnet[2]}.{random.randint(10, 254)}"


def _fetch_locations(connection) -> list[dict]:
    return run_query(
        connection,
        """
        SELECT location_id, building_name, room_number, rack_capacity, has_cooling, security_level
        FROM location
        ORDER BY location_id
        """,
    )


def _fetch_departments(connection) -> list[dict]:
    return run_query(
        connection,
        "SELECT dept_id, dept_name, is_active FROM department ORDER BY dept_id",
    )


def _fetch_assets(connection) -> list[dict]:
    return run_query(
        connection,
        """
        SELECT
            m.asset_id,
            m.hostname,
            m.status,
            m.location_id,
            m.dept_id,
            m.online_status,
            CASE
                WHEN s.asset_id IS NOT NULL THEN 'Server'
                WHEN w.asset_id IS NOT NULL THEN 'Workstation'
                WHEN n.asset_id IS NOT NULL THEN 'Network Device'
                ELSE 'Unknown'
            END AS device_class,
            s.rack_unit,
            s.cpu_count,
            s.ram_gb,
            w.assigned_user,
            w.form_factor,
            n.port_count,
            n.device_type
        FROM managed_assets m
        LEFT JOIN server s ON s.asset_id = m.asset_id
        LEFT JOIN workstation w ON w.asset_id = m.asset_id
        LEFT JOIN network_device n ON n.asset_id = m.asset_id
        ORDER BY m.asset_id
        """,
    )


def _fetch_assigned_users(connection) -> list[str]:
    rows = run_query(
        connection,
        """
        SELECT DISTINCT assigned_user
        FROM workstation
        WHERE assigned_user IS NOT NULL AND assigned_user <> ''
        ORDER BY assigned_user
        """,
    )
    return [row["assigned_user"] for row in rows]


def _asset_field_key(asset_id: str, field_name: str) -> str:
    return f"ops_update_{field_name}_{asset_id}"


def render_operations(go_home_callback: Callable[[], None], logout_callback: Callable[[], None]) -> None:
    top_left, _ = st.columns([1, 7])
    with top_left:
        if st.button("Home", width="stretch"):
            go_home_callback()
        if st.session_state.get("user") is not None:
            if st.button("Logout", key="logout_btn_operations"):
                logout_callback()

    st.markdown("## Operations")
    st.caption("CRUD workflows for device records. All writes use parameterized SQL and dropdown-based controls.")

    connection = connect_to_database()
    if not connection:
        st.error("Unable to connect to the database")
        return

    try:
        locations = _fetch_locations(connection)
        departments = _fetch_departments(connection)
        assets = _fetch_assets(connection)
        assigned_users = _fetch_assigned_users(connection)

        if not locations or not departments:
            st.error("Missing location or department reference data. CRUD operations cannot be rendered.")
            return

        location_by_id = {row["location_id"]: row for row in locations}
        building_options = sorted({row["building_name"] for row in locations})
        dept_ids = [row["dept_id"] for row in departments]
        dept_label_lookup = {
            row["dept_id"]: f"{row['dept_id']} | {row['dept_name']}"
            for row in departments
        }

        add_tab, update_tab, delete_tab = st.tabs(["Add Device", "Update Device", "Hard Remove"])

        with add_tab:
            st.markdown("### Add New Device")

            add_c1, add_c2, add_c3 = st.columns(3)
            with add_c1:
                add_device_class = st.selectbox("Device class", DEVICE_CLASS_OPTIONS, key="ops_add_device_class")
                add_building = st.selectbox("Location", building_options, key="ops_add_building")
                known_rooms = sorted({
                    str(row["room_number"]).upper() for row in locations if row["building_name"] == add_building
                })
                add_room_number = st.text_input(
                    "Room number",
                    value=known_rooms[0] if known_rooms else "",
                    key="ops_add_room",
                )
                if known_rooms:
                    st.caption(f"Known rooms in selected building: {', '.join(known_rooms)}")
                add_dept_id = st.selectbox(
                    "Department",
                    dept_ids,
                    format_func=lambda val: dept_label_lookup[val],
                    key="ops_add_dept",
                )
            with add_c2:
                add_status = st.selectbox("Status", STATUS_OPTIONS, key="ops_add_status")
                add_purchase_date = st.date_input("Purchase date", value=date.today(), key="ops_add_purchase")
                add_online_label = "Online" if add_status == "active" else "Offline"
                st.markdown(f"**Online state:** {add_online_label} (auto-set from status)")
            with add_c3:
                add_warranty_years = st.selectbox("Warranty (years)", [1, 2, 3, 4, 5], index=2, key="ops_add_warranty")

            add_room_valid = _is_valid_room_number(add_room_number)
            add_location_id = None
            add_existing_location_id = None
            if add_room_valid:
                add_existing_location_id = _resolve_location_id(locations, add_building, add_room_number)
                add_location_id = _resolve_or_build_location_id(locations, add_building, add_room_number)

            if not add_room_valid:
                st.error("Room number format is invalid. Use 3 digits, optionally followed by a letter (for example: 302 or 302B).")
            elif add_existing_location_id is None:
                st.info("This room is new for the selected building. A location record will be created when you save.")

            add_asset_id_preview = "-"
            add_hostname_preview = "-"
            add_ip_preview = "-"
            if add_location_id:
                add_asset_id_preview = _generate_asset_id(connection, add_device_class, add_location_id)
                add_hostname_preview = _generate_hostname(connection, add_device_class, add_location_id)
                add_ip_preview = _generate_ip_address(connection, add_location_id)

            st.markdown(
                f"""
                <div class="panel">
                    <h3>Auto-Generated Values</h3>
                    <p><strong>asset_id:</strong> {add_asset_id_preview}</p>
                    <p><strong>hostname:</strong> {add_hostname_preview}</p>
                    <p><strong>ip_address:</strong> {add_ip_preview}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            add_warranty_expiry = _add_years(add_purchase_date, add_warranty_years)
            add_online_status = 1 if add_status == "active" else 0

            add_assigned_user_value = None
            add_assigned_user_valid = True
            if add_device_class == "Server":
                sub_c1, sub_c2, sub_c3 = st.columns(3)
                with sub_c1:
                    add_rack_unit = st.selectbox("Rack unit", SERVER_RACK_UNITS, key="ops_add_server_rack")
                with sub_c2:
                    add_cpu_count = st.selectbox("CPU count", SERVER_CPU_OPTIONS, key="ops_add_server_cpu")
                with sub_c3:
                    add_ram_gb = st.selectbox("RAM (GB)", SERVER_RAM_OPTIONS, key="ops_add_server_ram")
            elif add_device_class == "Workstation":
                sub_c1, sub_c2 = st.columns(2)
                with sub_c1:
                    add_assigned_user_raw = st.text_input("Assigned user email (optional)", key="ops_add_ws_user_email")
                    add_assigned_user_value = add_assigned_user_raw.strip().lower() if add_assigned_user_raw else None
                    if add_assigned_user_value and not _is_valid_email(add_assigned_user_value):
                        add_assigned_user_valid = False
                        st.error("Assigned user email is invalid.")
                with sub_c2:
                    add_form_factor_options = sorted(set(WORKSTATION_FORM_FACTORS + [
                        row["form_factor"] for row in assets if row.get("form_factor")
                    ]))
                    add_form_factor = st.selectbox("Form factor", add_form_factor_options, key="ops_add_ws_form")
                if assigned_users:
                    st.caption("Email must be an @mix.wvu.edu email.")
            else:
                sub_c1, sub_c2 = st.columns(2)
                with sub_c1:
                    add_port_count = st.selectbox("Port count", NETWORK_PORT_OPTIONS, key="ops_add_nd_ports")
                with sub_c2:
                    add_device_type_options = sorted(set(NETWORK_DEVICE_TYPES + [
                        row["device_type"] for row in assets if row.get("device_type")
                    ]))
                    add_device_type = st.selectbox("Network device type", add_device_type_options, key="ops_add_nd_type")

            add_can_submit = add_location_id is not None and add_room_valid and add_assigned_user_valid

            if st.button(
                "Create device",
                key="ops_create_device",
                type="primary",
                width="stretch",
                disabled=not add_can_submit,
            ):
                try:
                    created_location_id = _ensure_location_exists(connection, locations, add_building, add_room_number)
                    created_asset_id = _generate_asset_id(connection, add_device_class, created_location_id)
                    created_hostname = _generate_hostname(connection, add_device_class, created_location_id)
                    created_ip = _generate_ip_address(connection, created_location_id)

                    run_query(
                        connection,
                        """
                        INSERT INTO managed_assets
                        (asset_id, hostname, ip_address, status, purchase_date, warranty_expiry_date, location_id, dept_id, online_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            created_asset_id,
                            created_hostname,
                            created_ip,
                            add_status,
                            add_purchase_date,
                            add_warranty_expiry,
                            created_location_id,
                            add_dept_id,
                            add_online_status,
                        ),
                        commit=False,
                    )

                    if add_device_class == "Server":
                        run_query(
                            connection,
                            "INSERT INTO server (asset_id, rack_unit, cpu_count, ram_gb) VALUES (%s, %s, %s, %s)",
                            (created_asset_id, add_rack_unit, add_cpu_count, add_ram_gb),
                            commit=False,
                        )
                    elif add_device_class == "Workstation":
                        run_query(
                            connection,
                            "INSERT INTO workstation (asset_id, assigned_user, form_factor) VALUES (%s, %s, %s)",
                            (created_asset_id, add_assigned_user_value, add_form_factor),
                            commit=False,
                        )
                    else:
                        run_query(
                            connection,
                            "INSERT INTO network_device (asset_id, port_count, device_type) VALUES (%s, %s, %s)",
                            (created_asset_id, add_port_count, add_device_type),
                            commit=False,
                        )

                    connection.commit()
                    st.success(f"Device created: {created_asset_id}")
                    st.rerun()
                except Exception as e:
                    connection.rollback()
                    st.error("Failed to create device")
                    st.write(e)

        with update_tab:
            st.markdown("### Update Device")

            if not assets:
                st.info("No device records found.")
            else:
                asset_lookup = {row["asset_id"]: row for row in assets}
                asset_ids = list(asset_lookup.keys())
                asset_label_lookup = {
                    row["asset_id"]: f"{row['asset_id']} | {row['hostname']} | {row['device_class']} | {row['status']}"
                    for row in assets
                }

                selected_asset_id = st.selectbox(
                    "Select device",
                    asset_ids,
                    format_func=lambda val: asset_label_lookup[val],
                    key="ops_update_asset",
                )
                current = asset_lookup[selected_asset_id]

                st.caption(
                    f"Current: location={current['location_id']} | department={current['dept_id']} | status={current['status']}"
                )

                current_location_meta = location_by_id.get(current["location_id"], {})
                current_building = current_location_meta.get("building_name", building_options[0])
                current_room_number = str(current_location_meta.get("room_number", ""))

                status_key = _asset_field_key(selected_asset_id, "status")
                building_key = _asset_field_key(selected_asset_id, "building")
                room_key = _asset_field_key(selected_asset_id, "room")
                dept_key = _asset_field_key(selected_asset_id, "dept")
                id_mode_key = _asset_field_key(selected_asset_id, "id_mode")

                update_c1, update_c2, update_c3 = st.columns(3)
                with update_c1:
                    update_status = st.selectbox(
                        "Status",
                        STATUS_OPTIONS,
                        index=STATUS_OPTIONS.index(current["status"]) if current["status"] in STATUS_OPTIONS else 0,
                        key=status_key,
                    )
                    update_building = st.selectbox(
                        "Location",
                        building_options,
                        index=building_options.index(current_building) if current_building in building_options else 0,
                        key=building_key,
                    )
                    update_known_rooms = sorted({
                        str(row["room_number"]).upper() for row in locations if row["building_name"] == update_building
                    })
                    update_room_number = st.text_input(
                        "Room number",
                        value=current_room_number,
                        key=room_key,
                    )
                    if update_known_rooms:
                        st.caption(f"Known rooms in selected building: {', '.join(update_known_rooms)}")
                with update_c2:
                    update_dept_id = st.selectbox(
                        "Department",
                        dept_ids,
                        index=dept_ids.index(current["dept_id"]) if current["dept_id"] in dept_ids else 0,
                        format_func=lambda val: dept_label_lookup[val],
                        key=dept_key,
                    )
                    update_online_label = "Online" if update_status == "active" else "Offline"
                    st.markdown(f"**Online state:** {update_online_label} (auto-set from status)")
                with update_c3:
                    update_id_mode = st.selectbox(
                        "Asset ID update",
                        ["Keep current", "Regenerate for location"],
                        key=id_mode_key,
                    )

                update_room_valid = _is_valid_room_number(update_room_number)
                update_location_id = None
                update_existing_location_id = None
                if update_room_valid:
                    update_existing_location_id = _resolve_location_id(locations, update_building, update_room_number)
                    update_location_id = _resolve_or_build_location_id(locations, update_building, update_room_number)

                if not update_room_valid:
                    st.error("Room number format is invalid. Use 3 digits, optionally followed by a letter (for example: 302 or 302B).")
                elif update_existing_location_id is None:
                    st.info("This room is new for the selected building. A location record will be created when you save.")

                regen_asset_id = None
                regen_hostname = None
                can_regenerate_id = current["device_class"] in DEVICE_PREFIX_MAP and current["device_class"] in HOSTNAME_TYPE_MAP
                if update_location_id and can_regenerate_id:
                    regen_asset_id = _generate_asset_id(
                        connection,
                        current["device_class"],
                        update_location_id,
                        exclude_asset_id=selected_asset_id,
                    )
                    regen_hostname = _generate_hostname(
                        connection,
                        current["device_class"],
                        update_location_id,
                        exclude_asset_id=selected_asset_id,
                    )

                if update_id_mode == "Regenerate for location" and not can_regenerate_id:
                    st.error("This device does not have a recognized subtype, so asset_id regeneration is unavailable.")

                if update_id_mode == "Regenerate for location" and regen_asset_id and regen_hostname:
                    st.info(f"New asset_id: {regen_asset_id} | New hostname: {regen_hostname}")

                update_assigned_user_value = None
                update_assigned_user_valid = True
                if current["device_class"] == "Server":
                    update_rack_key = _asset_field_key(selected_asset_id, "server_rack")
                    update_cpu_key = _asset_field_key(selected_asset_id, "server_cpu")
                    update_ram_key = _asset_field_key(selected_asset_id, "server_ram")

                    server_c1, server_c2, server_c3 = st.columns(3)
                    with server_c1:
                        update_rack_unit = st.selectbox(
                            "Rack unit",
                            SERVER_RACK_UNITS,
                            index=SERVER_RACK_UNITS.index(current["rack_unit"]) if current.get("rack_unit") in SERVER_RACK_UNITS else 0,
                            key=update_rack_key,
                        )
                    with server_c2:
                        update_cpu_count = st.selectbox(
                            "CPU count",
                            SERVER_CPU_OPTIONS,
                            index=SERVER_CPU_OPTIONS.index(int(current["cpu_count"])) if current.get("cpu_count") in SERVER_CPU_OPTIONS else 0,
                            key=update_cpu_key,
                        )
                    with server_c3:
                        update_ram_gb = st.selectbox(
                            "RAM (GB)",
                            SERVER_RAM_OPTIONS,
                            index=SERVER_RAM_OPTIONS.index(int(current["ram_gb"])) if current.get("ram_gb") in SERVER_RAM_OPTIONS else 0,
                            key=update_ram_key,
                        )
                elif current["device_class"] == "Workstation":
                    current_user = (current.get("assigned_user") or "").strip()
                    ws_form_options = sorted(set(WORKSTATION_FORM_FACTORS + [
                        row["form_factor"] for row in assets if row.get("form_factor")
                    ]))
                    update_user_key = _asset_field_key(selected_asset_id, "ws_user_email")
                    update_form_key = _asset_field_key(selected_asset_id, "ws_form")

                    ws_c1, ws_c2 = st.columns(2)
                    with ws_c1:
                        update_assigned_user_raw = st.text_input(
                            "Assigned user email (optional)",
                            value=current_user,
                            key=update_user_key,
                        )
                        update_assigned_user_value = update_assigned_user_raw.strip().lower() if update_assigned_user_raw else None
                        if update_assigned_user_value and not _is_valid_email(update_assigned_user_value):
                            update_assigned_user_valid = False
                            st.error("Assigned user email is invalid.")
                    with ws_c2:
                        update_form_factor = st.selectbox(
                            "Form factor",
                            ws_form_options,
                            index=ws_form_options.index(current["form_factor"]) if current.get("form_factor") in ws_form_options else 0,
                            key=update_form_key,
                        )
                    st.caption("Email must be an @mix.wvu.edu email.")
                elif current["device_class"] == "Network Device":
                    nd_type_options = sorted(set(NETWORK_DEVICE_TYPES + [
                        row["device_type"] for row in assets if row.get("device_type")
                    ]))
                    update_ports_key = _asset_field_key(selected_asset_id, "nd_ports")
                    update_nd_type_key = _asset_field_key(selected_asset_id, "nd_type")

                    nd_c1, nd_c2 = st.columns(2)
                    with nd_c1:
                        update_port_count = st.selectbox(
                            "Port count",
                            NETWORK_PORT_OPTIONS,
                            index=NETWORK_PORT_OPTIONS.index(int(current["port_count"])) if current.get("port_count") in NETWORK_PORT_OPTIONS else 0,
                            key=update_ports_key,
                        )
                    with nd_c2:
                        update_device_type = st.selectbox(
                            "Network device type",
                            nd_type_options,
                            index=nd_type_options.index(current["device_type"]) if current.get("device_type") in nd_type_options else 0,
                            key=update_nd_type_key,
                        )

                update_can_submit = (
                    update_location_id is not None
                    and update_room_valid
                    and update_assigned_user_valid
                    and (update_id_mode != "Regenerate for location" or (regen_asset_id is not None and regen_hostname is not None))
                )

                if st.button(
                    "Apply update",
                    key="ops_apply_update",
                    type="primary",
                    width="stretch",
                    disabled=not update_can_submit,
                ):
                    try:
                        saved_location_id = _ensure_location_exists(connection, locations, update_building, update_room_number)

                        update_online_status = 1 if update_status == "active" else 0

                        final_asset_id = selected_asset_id
                        final_hostname = current["hostname"]
                        if update_id_mode == "Regenerate for location":
                            final_asset_id = regen_asset_id
                            final_hostname = regen_hostname

                        run_query(
                            connection,
                            """
                            UPDATE managed_assets
                            SET asset_id = %s,
                                hostname = %s,
                                status = %s,
                                location_id = %s,
                                dept_id = %s,
                                online_status = %s
                            WHERE asset_id = %s
                            """,
                            (
                                final_asset_id,
                                final_hostname,
                                update_status,
                                saved_location_id,
                                update_dept_id,
                                update_online_status,
                                selected_asset_id,
                            ),
                            commit=False,
                        )

                        if current["device_class"] == "Server":
                            run_query(
                                connection,
                                """
                                UPDATE server
                                SET asset_id = %s, rack_unit = %s, cpu_count = %s, ram_gb = %s
                                WHERE asset_id IN (%s, %s)
                                """,
                                (
                                    final_asset_id,
                                    update_rack_unit,
                                    update_cpu_count,
                                    update_ram_gb,
                                    selected_asset_id,
                                    final_asset_id,
                                ),
                                commit=False,
                            )
                        elif current["device_class"] == "Workstation":
                            run_query(
                                connection,
                                """
                                UPDATE workstation
                                SET asset_id = %s, assigned_user = %s, form_factor = %s
                                WHERE asset_id IN (%s, %s)
                                """,
                                (
                                    final_asset_id,
                                    update_assigned_user_value,
                                    update_form_factor,
                                    selected_asset_id,
                                    final_asset_id,
                                ),
                                commit=False,
                            )
                        elif current["device_class"] == "Network Device":
                            run_query(
                                connection,
                                """
                                UPDATE network_device
                                SET asset_id = %s, port_count = %s, device_type = %s
                                WHERE asset_id IN (%s, %s)
                                """,
                                (
                                    final_asset_id,
                                    update_port_count,
                                    update_device_type,
                                    selected_asset_id,
                                    final_asset_id,
                                ),
                                commit=False,
                            )

                        connection.commit()
                        st.success(f"Device updated: {final_asset_id}")
                        st.rerun()
                    except Exception as e:
                        connection.rollback()
                        st.error("Failed to update device")
                        st.write(e)

        with delete_tab:
            st.markdown("### Hard Remove Device")
            st.warning("This action permanently deletes the asset from device tables and cannot be undone.")

            if not assets:
                st.info("No device records found.")
            else:
                asset_lookup = {row["asset_id"]: row for row in assets}
                asset_ids = list(asset_lookup.keys())
                delete_asset_id = st.selectbox("Device to delete", asset_ids, key="ops_delete_asset")
                delete_current = asset_lookup[delete_asset_id]

                st.caption(
                    f"Selected: {delete_current['asset_id']} | {delete_current['hostname']} | {delete_current['device_class']}"
                )

                confirm_delete_a = st.checkbox(
                    "I understand this will permanently remove the selected asset from database device tables.",
                    key="ops_delete_confirm_a",
                )
                confirm_delete_b = st.checkbox(
                    f"Yes, delete {delete_asset_id}.",
                    key="ops_delete_confirm_b",
                )

                if st.button("Hard delete device", key="ops_delete_submit", type="primary", width="stretch"):
                    if not (confirm_delete_a and confirm_delete_b):
                        st.error("Please complete both confirmations before deleting.")
                    else:
                        try:
                            maintenance_rows = run_query(
                                connection,
                                "SELECT COUNT(*) AS cnt FROM maintenance_log WHERE asset_id = %s",
                                (delete_asset_id,),
                            )
                            maintenance_count = int(maintenance_rows[0]["cnt"]) if maintenance_rows else 0
                            if maintenance_count > 0:
                                st.error(
                                    "Hard delete blocked: maintenance_log rows exist for this asset. "
                                    "Retire the asset or clear dependent logs first."
                                )
                                return

                            subtype_table_map = {
                                "Server": "server",
                                "Workstation": "workstation",
                                "Network Device": "network_device",
                            }
                            subtype_table = subtype_table_map.get(delete_current["device_class"])
                            if subtype_table:
                                run_query(
                                    connection,
                                    f"DELETE FROM {subtype_table} WHERE asset_id = %s",
                                    (delete_asset_id,),
                                    commit=False,
                                )

                            run_query(
                                connection,
                                "DELETE FROM managed_assets WHERE asset_id = %s",
                                (delete_asset_id,),
                                commit=False,
                            )
                            connection.commit()
                            st.success(f"Device deleted: {delete_asset_id}")
                            st.rerun()
                        except Exception as e:
                            connection.rollback()
                            st.error("Failed to hard delete device")
                            st.write(e)
    finally:
        try:
            connection.close()
        except Exception:
            pass
