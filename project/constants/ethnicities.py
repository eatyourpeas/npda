from project.constants import colors


ETHNICITIES = (
    ("N", "African"),
    ("L", "Any other Asian background"),
    ("P", "Any other Black background"),
    ("S", "Any other ethnic group"),
    ("G", "Any other mixed background"),
    ("C", "Any other White background"),
    ("K", "Bangladeshi or British Bangladeshi"),
    ("A", "British, Mixed British"),
    ("M", "Caribbean"),
    ("R", "Chinese"),
    ("H", "Indian or British Indian"),
    ("B", "Irish"),
    ("Z", "Not Stated"),
    ("J", "Pakistani or British Pakistani"),
    ("F", "Mixed (White and Asian)"),
    ("E", "Mixed (White and Black African)"),
    ("D", "Mixed (White and Black Caribbean)"),
    ("99", "Not known"),
)

# Define top-level ethnicity categories and their colors (RCPCH defined)
ETHNICITY_PARENT_COLOR_MAP = {
    "White": colors.RCPCH_LIGHT_BLUE,
    "Asian": colors.RCPCH_PINK,
    "Black": colors.RCPCH_MID_GREY,
    "Mixed": colors.RCPCH_YELLOW,
    "Other": colors.RCPCH_DARK_BLUE,
}

# Define ethnicity mapping to parents
ETHNICITY_CHILD_PARENT_MAP = {
    "Not known": "Other",
    "Any other mixed background": "Mixed",
    "African": "Black",
    "Pakistani or British Pakistani": "Asian",
    "Caribbean": "Black",
    "British, Mixed British": "White",
    "Any other White background": "White",
    "Any other Black background": "Black",
    "Mixed (White and Black Caribbean)": "Mixed",
    "Irish": "White",
    "Any other ethnic group": "Other",
    "Chinese": "Asian",
    "Any other Asian background": "Asian",
    "Mixed (White and Asian)": "Mixed",
    "Indian or British Indian": "Asian",
    "Not Stated": "Other",
    "Mixed (White and Black African)": "Mixed",
    "Bangladeshi or British Bangladeshi": "Asian",
}
