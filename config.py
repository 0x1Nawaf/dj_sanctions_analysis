DJ_BASE_URL = "https://djrcfeed.dowjones.com/xml/"

FEED_SCOPE_COMPLETE = "complete"
FEED_SCOPE_DELTA = "delta_only"
FEED_SCOPES = (FEED_SCOPE_COMPLETE, FEED_SCOPE_DELTA)

# PFA root @type values that denote a snapshot of the whole record universe.
# Only such a file lets the seeder inactivate records absent from it.
FULL_SNAPSHOT_PFA_TYPES = frozenset(("full", "f", "complete", "snapshot"))


def feed_scope_from_pfa_type(pfa_type):
    """Derive the seeder's feed_scope from the PFA root element's @type.

    Unrecognised and missing types resolve to delta_only. Mislabelling a delta
    as complete makes the seeder inactivate every record absent from the file,
    so anything short of a positively identified full snapshot is treated as
    partial.
    """
    if pfa_type and pfa_type.strip().lower() in FULL_SNAPSHOT_PFA_TYPES:
        return FEED_SCOPE_COMPLETE
    return FEED_SCOPE_DELTA

DOWNLOAD_TIMEOUT = 600

DOWNLOAD_CHUNK_SIZE = 1024 * 1024

CHILD_TABLES = [
    "record_name",
    "record_description",
    "record_role",
    "record_date",
    "record_birth_place",
    "record_sanctions_ref",
    "record_country",
    "record_id_number",
    "record_source",
    "record_image",
    "record_address",
]
