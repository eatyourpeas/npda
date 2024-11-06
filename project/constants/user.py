VIEW_PREFERENCES = (
    (0, "organisation"),
    (1, "trust"),
    (2, "national"),
)

AUDIT_CENTRE_COORDINATOR = 1
AUDIT_CENTRE_EDITOR = 2
AUDIT_CENTRE_READER = 3
RCPCH_AUDIT_TEAM = 4
RCPCH_AUDIT_PATIENT_FAMILY = 7

ROLES = (
    (AUDIT_CENTRE_COORDINATOR, "Coordinator"),
    (AUDIT_CENTRE_EDITOR, "Editor"),
    (AUDIT_CENTRE_READER, "Reader"),
    (RCPCH_AUDIT_TEAM, "RCPCH Audit Team"),
    (RCPCH_AUDIT_PATIENT_FAMILY, "RCPCH Audit Children and Family"),
)

AUDIT_CENTRE_ROLES = (
    (AUDIT_CENTRE_COORDINATOR, "Coordinator"),
    (AUDIT_CENTRE_EDITOR, "Editor"),
    (AUDIT_CENTRE_READER, "Reader"),
)

RCPCH_AUDIT_TEAM_ROLES = ((RCPCH_AUDIT_TEAM, "RCPCH Audit Team"),)

MR = 1
MRS = 2
MS = 3
DR = 4
PROFESSOR = 5

TITLES = ((MR, "Mr"), (MRS, "Mrs"), (MS, "Ms"), (DR, "Dr"), (PROFESSOR, "Professor"))

"""
Groups
These map to the roles
Role                                Group
Audit Centre Coordinator            trust_audit_team_coordinator_access
Audit Centre Editor                 trust_audit_team_edit_access
Audit Centre Reader                 trust_audit_team_view_only
RCPCH Audit Team                    npda_audit_team_full_access
RCPCH Audit Children and Family     patient_access
"""
# logged in user access all areas: can create/update/delete any audit data, logs, npda key words and organisation trusts, groups and permissions
NPDA_AUDIT_TEAM_FULL_ACCESS = "npda_audit_team_full_access"

# logged in user can view all data relating to their trust(s) but not logs
TRUST_AUDIT_TEAM_VIEW_ONLY = "trust_audit_team_view_only"

# logged in user can edit but not delete all data relating to their trust(s) but not view or edit logs, npda key words and organisation trusts, groups and permissions
TRUST_AUDIT_TEAM_EDIT_ACCESS = "trust_audit_team_edit_access"

# logged in user can delete all data relating to their trust(s) but not view or edit logs, npda key words and organisation trusts, groups and permissions
TRUST_AUDIT_TEAM_COORDINATOR_ACCESS = "trust_audit_team_coordinator_access"

# logged in user can view their own audit data, consent to participation and remove that consent/opt out. Opting out would delete all data relating to them, except the npda unique identifier
PATIENT_ACCESS = "patient_access"

GROUPS = (
    NPDA_AUDIT_TEAM_FULL_ACCESS,
    TRUST_AUDIT_TEAM_VIEW_ONLY,
    TRUST_AUDIT_TEAM_EDIT_ACCESS,
    TRUST_AUDIT_TEAM_COORDINATOR_ACCESS,
    PATIENT_ACCESS,
)

"""
Custom permissions
"""

# Patient
CAN_LOCK_CHILD_PATIENT_DATA_FROM_EDITING = (
    "can_lock_child_patient_data_from_editing",
    "Can lock a child's record from editing.",
)
CAN_UNLOCK_CHILD_PATIENT_DATA_FROM_EDITING = (
    "can_unlock_child_patient_data_from_editing",
    "Can unlock a child's record from editing.",
)
CAN_OPT_OUT_CHILD_FROM_INCLUSION_IN_AUDIT = (
    "can_opt_out_child_from_inclusion_in_audit",
    "Can sanction an opt out from participating in the audit. Note all the child's date except NPDA unique identifier are irretrievably deleted.",
)

CAN_ALLOCATE_NPDA_LEAD_CENTRE = (
    "can_allocate_npda_lead_centre",
    "Can allocate this child to any NPDA centre.",
)

CAN_TRANSFER_NPDA_LEAD_CENTRE = (
    "can_transfer_npda_lead_centre",
    "Can transfer this child to another NPDA centre.",
)

CAN_EDIT_NPDA_LEAD_CENTRE = (
    "can_edit_npda_lead_centre",
    "Can edit this child's current NPDA lead centre.",
)

CAN_DELETE_NPDA_LEAD_CENTRE = (
    "can_delete_npda_lead_centre",
    "Can delete NPDA lead centre.",
)

# Organisation
CAN_PUBLISH_NPDA_DATA = (
    "can_publish_npda_data",
    "Can publish NPDA data to public facing site.",
)

CAN_CONSENT_TO_AUDIT_PARTICIPATION = (
    # Not actively used - can be applied to patients in future
    "can_consent_to_audit_participation",
    "Can consent to participating in NPDA.",
)

CAN_UPLOAD_CSV = (
    "can_upload_csv",
    "Can upload CSV files.",
)

CAN_COMPLETE_QUESTIONNAIRE = (
    "can_complete_questionnaire",
    "Can complete questionnaires.",
)

PERMISSIONS = (
    CAN_LOCK_CHILD_PATIENT_DATA_FROM_EDITING,
    CAN_UNLOCK_CHILD_PATIENT_DATA_FROM_EDITING,
    CAN_OPT_OUT_CHILD_FROM_INCLUSION_IN_AUDIT,
    CAN_EDIT_NPDA_LEAD_CENTRE,
    CAN_ALLOCATE_NPDA_LEAD_CENTRE,
    CAN_TRANSFER_NPDA_LEAD_CENTRE,
    CAN_DELETE_NPDA_LEAD_CENTRE,
    CAN_CONSENT_TO_AUDIT_PARTICIPATION,
    CAN_PUBLISH_NPDA_DATA,
    CAN_UPLOAD_CSV,
    CAN_COMPLETE_QUESTIONNAIRE,
)
