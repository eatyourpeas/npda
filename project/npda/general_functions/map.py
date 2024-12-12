# python imports
import json
import os
import requests

# django imports
from django.conf import settings
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.apps import apps

# third-party imports
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go

# RCPCH imports
from project.constants import (
    RCPCH_PINK_DARK_TINT,
    RCPCH_PINK,
    RCPCH_PINK_LIGHT_TINT3,
    RCPCH_PINK_LIGHT_TINT2,
    RCPCH_PINK_LIGHT_TINT1,
    RCPCH_LIGHT_BLUE_TINT3,
    RCPCH_LIGHT_BLUE_TINT2,
    RCPCH_LIGHT_BLUE_TINT1,
    RCPCH_LIGHT_BLUE,
    RCPCH_LIGHT_BLUE_DARK_TINT,
    RCPCH_DARK_BLUE,
)
from project.npda.general_functions.validate_postcode import location_for_postcode

"""
Functions to return scatter plot of children by postcode
"""


def load_wales_lsoa_shp():
    file_path = os.path.join(
        settings.BASE_DIR,
        "project",
        "constants",
        "English IMD 2019",
        "wimd2019.json",
    )
    gdf = gpd.read_file(file_path)
    return gdf


def get_children_by_pdu_audit_year(
    audit_year, paediatric_diabetes_unit, paediatric_diabetes_unit_lead_organisation
):
    """
    Returns a list of children by postcode for a given audit year and paediatric diabetes unit
    """
    Patient = apps.get_model("npda", "Patient")
    Submission = apps.get_model("npda", "Submission")

    submission = Submission.objects.filter(
        audit_year=audit_year, paediatric_diabetes_unit=paediatric_diabetes_unit
    ).first()

    if submission is None:
        return Patient.objects.none()

    patients = submission.patients.all()

    if patients:
        filtered_patients = patients.filter(
            ~Q(postcode__isnull=True)
            | ~Q(postcode__exact=""),  # Exclude patients with no postcode
        )

        for patient in filtered_patients:
            if patient.postcode:
                # this currently takes a long time to run because of the API call - once we save the location data in the database on save, we can remove this
                lon, lat, location_wgs84, location_bng = location_for_postcode(
                    patient.postcode
                )
                patient.location_wgs84 = location_wgs84
                patient.location_bng = location_bng
                patient.save()

        filtered_patients = filtered_patients.annotate(
            distance_from_lead_organisation=Distance(
                "location_wgs84",
                Point(
                    paediatric_diabetes_unit_lead_organisation["longitude"],
                    paediatric_diabetes_unit_lead_organisation["latitude"],
                    srid=4326,
                ),
            )
        ).values(
            "pk",
            "location_bng",
            "location_wgs84",
            "distance_from_lead_organisation",
        )

        return filtered_patients

    else:
        return Patient.objects.none()


def generate_distance_from_organisation_scatterplot_figure(
    geo_df: pd.DataFrame, pdu_lead_organisation, pdu
) -> go.Figure:
    """
    Returns a plottable map with Cases overlayed as dots with tooltips on hover

    2011 LSOAs mapped to 2019 IMD data is a service fortunately already provided by
    [Consumer Data Research Centre](https://data.cdrc.ac.uk/dataset/index-multiple-deprivation-imd)
    and stored here as a shapefile. This is then converted to a GeoJSON file for use in the map.
    """

    custom_colorscale = [
        [0, RCPCH_PINK_DARK_TINT],  # Very dark pink
        [0.11, RCPCH_PINK],  # pink
        [0.22, RCPCH_PINK_LIGHT_TINT1],  # Medium light pink
        [0.33, RCPCH_PINK_LIGHT_TINT2],  # light pink
        [0.44, RCPCH_PINK_LIGHT_TINT3],  # very light pink
        [0.55, RCPCH_LIGHT_BLUE_TINT3],  # Very light blue
        [0.66, RCPCH_LIGHT_BLUE_TINT2],  # Light blue
        [0.77, RCPCH_LIGHT_BLUE_TINT1],  # Medium light blue
        [0.88, RCPCH_LIGHT_BLUE],  # blue
        [1, RCPCH_LIGHT_BLUE_DARK_TINT],  # Dark blue
    ]

    # # Load the IMD data
    if pdu.paediatric_diabetes_network_code == "PN07":
        file_path = os.path.join(
            settings.BASE_DIR,
            "project",
            "constants",
            "English IMD 2019",
            "merged_lsoa_wales.json",
        )
    else:
        file_path = os.path.join(
            settings.BASE_DIR,
            "project",
            "constants",
            "English IMD 2019",
            "merged_lsoa_england.json",
        )
    gdf = gpd.GeoDataFrame.from_file(file_path)

    # Create a Plotly choropleth map coloured by IMD Rank
    fig = go.Figure(
        go.Choroplethmapbox(
            geojson=gdf.__geo_interface__,
            locations=gdf["LSOA11CD"],
            featureidkey="properties.LSOA11CD",
            z=gdf["Index of Multiple Deprivation (IMD) Rank"],
            colorscale=custom_colorscale,
            marker_line_width=0,
            marker_opacity=0.5,
            customdata=gdf[
                ["LSOA11NM", "Index of Multiple Deprivation (IMD) Decile"]
            ].to_numpy(),
            hovertemplate="<b>%{customdata[0]}</b><br>IMD Decile: %{customdata[1]}<extra></extra>",  # Custom hover template
        )
    )

    # add the Organisation as a scatterplot in blue
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=10,
        mapbox_center=dict(
            lat=pdu_lead_organisation["latitude"],
            lon=pdu_lead_organisation["longitude"],
        ),
        height=590,
        mapbox_accesstoken=settings.MAPBOX_API_KEY,
        showlegend=False,
    )

    # Add a scatterplot point for the organization
    fig.add_trace(
        go.Scattermapbox(
            lat=[pdu_lead_organisation["latitude"]],
            lon=[pdu_lead_organisation["longitude"]],
            mode="markers",
            marker=go.scattermapbox.Marker(
                size=12,
                color=RCPCH_DARK_BLUE,  # Set the color of the point
            ),
            text=[pdu_lead_organisation["name"]],  # Set the hover text for the point
            showlegend=False,
        )
    )

    if not geo_df.empty:
        # add the Patients as a scatterplot in pink, with distance to the lead organisation as hover text
        fig.add_trace(
            go.Scattermapbox(
                # Extract latitude and longitude from the point objects
                lat=geo_df["location_wgs84"].apply(lambda point: point.y),
                lon=geo_df["location_wgs84"].apply(lambda point: point.x),
                mode="markers",
                marker=go.scattermapbox.Marker(
                    size=8,
                    color=RCPCH_PINK,  # Set the color of the point
                ),
                text=geo_df["distance_km"],  # Set the hover text for the point
                customdata=geo_df[
                    ["pk", "distance_mi", "distance_km"]
                ].to_numpy(),  # Add custom data for hover
                hovertemplate="<b>NPDA ID: %{customdata[0]}</b><br>Distance to Lead Centre: %{customdata[1]:.2f} mi (%{customdata[2]:.2f} km)<extra></extra>",  # Custom hovertemplate just for the lead organisation
                showlegend=False,
            )
        )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        font=dict(family="Montserrat-Regular", color="#FFFFFF"),
        hoverlabel=dict(
            bgcolor=RCPCH_LIGHT_BLUE,
            font_size=12,
            font=dict(color="white", family="montserrat"),
            bordercolor=RCPCH_LIGHT_BLUE,
        ),
        mapbox=dict(
            style="carto-positron",
            zoom=10,
            center=dict(
                lat=pdu_lead_organisation["latitude"],
                lon=pdu_lead_organisation["longitude"],
            ),
        ),
        mapbox_layers=[
            {
                "below": "traces",
                "sourcetype": "raster",
                "sourceattribution": "Source: Office for National Statistics licensed under the Open Government Licence v.3.0",
                "source": [
                    "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                ],
            }
        ],
    )

    return fig


def generate_dataframe_and_aggregated_distance_data_from_cases(filtered_cases):
    """
    Returns a dataframe of all Cases, location data and distances with aggregated results
    Returns it as a tuple of two dataframes, one for the cases and the distances from the lead organisation, the other for the aggregated distances (max, mean, median, std)
    """

    geo_df = pd.DataFrame(filtered_cases)

    if not geo_df.empty:
        if "location_wgs84" in geo_df.columns:
            geo_df["longitude"] = geo_df["location_wgs84"].apply(lambda loc: loc.x)
            geo_df["latitude"] = geo_df["location_wgs84"].apply(lambda loc: loc.y)
            geo_df["distance_km"] = geo_df["distance_from_lead_organisation"].apply(
                lambda d: d.km
            )
            geo_df["distance_mi"] = geo_df["distance_from_lead_organisation"].apply(
                lambda d: d.mi
            )

            max_distance_travelled_km = geo_df["distance_km"].min()
            mean_distance_travelled_km = geo_df["distance_km"].mean()
            median_distance_travelled_km = geo_df["distance_km"].median()
            std_distance_travelled_km = geo_df["distance_km"].std()

            max_distance_travelled_mi = geo_df["distance_mi"].min()
            mean_distance_travelled_mi = geo_df["distance_mi"].mean()
            median_distance_travelled_mi = geo_df["distance_mi"].median()
            std_distance_travelled_mi = geo_df["distance_mi"].std()

            return {
                "max_distance_travelled_km": f"{max_distance_travelled_km:.2f}",
                "mean_distance_travelled_km": f"{mean_distance_travelled_km:.2f}",
                "median_distance_travelled_km": f"{median_distance_travelled_km:.2f}",
                "std_distance_travelled_km": f"{std_distance_travelled_km:.2f}",
                "max_distance_travelled_mi": f"{max_distance_travelled_mi:.2f}",
                "mean_distance_travelled_mi": f"{mean_distance_travelled_mi:.2f}",
                "median_distance_travelled_mi": f"{median_distance_travelled_mi:.2f}",
                "std_distance_travelled_mi": f"{std_distance_travelled_mi:.2f}",
            }, geo_df
    else:
        geo_df["pk"] = None
        geo_df["longitude"] = None
        geo_df["latitude"] = None
        geo_df["distance_km"] = 0
        geo_df["distance_mi"] = 0
        return {
            "max_distance_travelled_km": f"~",
            "mean_distance_travelled_km": f"~",
            "median_distance_travelled_km": f"~",
            "std_distance_travelled_km": f"~",
            "max_distance_travelled_mi": f"~",
            "mean_distance_travelled_mi": f"~",
            "median_distance_travelled_mi": f"~",
            "std_distance_travelled_mi": f"~",
        }, geo_df


def generate_geojson_of_imd_and_lsoa_boundaries_for_country(country="england"):
    """
    lsoa 2011 boundaries and identifiers - 34753 records (England & Wales): "LSOA_2011_Boundaries_Super_Generalised_Clipped_BSC_EW_V4_8608708935797446279.geojson
    imd England 2019 data - 32844 records (England): "IMD2019.xlsx"
    imd Wales 2019 data - 1909 records (Wales): "Index_of_Multiple_Deprivation_(Dec_2019)_Lookup_in_Wales.geojson

    This generates two files (one for England and one for Wales) that contain the merged LSOA boundaries and IMD data as GeoJSON files
    This is used to generate the choropleth map of IMD data

    This function is only used to generate the files and should not be called in production
    """

    file_path = os.path.join(
        settings.BASE_DIR,
        "project",
        "constants",
        "English IMD 2019",
        "LSOA_2011_Boundaries_Super_Generalised_Clipped_BSC_EW_V4_8608708935797446279.geojson",
    )
    england_wales_lsoas = gpd.read_file(file_path)  # 34753 LSOAs

    path = os.path.join(
        settings.BASE_DIR,
        "project",
        "constants",
        "English IMD 2019",
        "IMD2019.xlsx",
    )
    england_imd = pd.read_excel(
        path, sheet_name="IMD2019"
    )  # 32844 LSOAs: IMD data for England 2019 without geometry

    file_path = os.path.join(
        settings.BASE_DIR,
        "project",
        "constants",
        "English IMD 2019",
        "Index_of_Multiple_Deprivation_(Dec_2019)_Lookup_in_Wales.geojson",
    )
    wales_imd = gpd.read_file(
        file_path
    )  # 1909 LSOAs: IMD data for Wales 2019 without geometry

    # Rename columns in wales_gdf to match england_imd
    wales_imd = wales_imd.rename(
        columns={
            "lsoa11cd": "LSOA code (2011)",
            "lsoa11nm": "LSOA name (2011)",
            "lsoa11nmw": "LSOA name (2011) (Welsh)",
            "wimd_2019": "Index of Multiple Deprivation (IMD) Rank",
        }
    )

    # convert Index of Multiple Deprivation (IMD) Rank to to decile with name Index of Multiple Deprivation (IMD) Decile
    wales_imd["Index of Multiple Deprivation (IMD) Decile"] = pd.qcut(
        wales_imd["Index of Multiple Deprivation (IMD) Rank"], 10, labels=False
    )

    # remove the empty geometry column from Wales
    # wales_imd.drop(columns=["geometry"])

    if country == "England":
        # merge the england&wales imd data with the england&wales geodataframe
        england_wales_lsoas = england_wales_lsoas.merge(
            england_imd, left_on="LSOA11CD", right_on="LSOA code (2011)", how="left"
        )  # 34753 LSOAs
    else:
        england_wales_lsoas = england_wales_lsoas.merge(
            wales_imd,
            left_on="LSOA11CD",
            right_on="LSOA code (2011)",
            how="left",
            suffixes=("", "_wales"),
        )
        england_wales_lsoas.drop(columns=["geometry_wales"], inplace=True)

    england_wales_lsoas = england_wales_lsoas.to_crs(epsg=4326)
    england_wales_lsoas = england_wales_lsoas.__geo_interface__

    # # convert the data to geojson
    with open(f"merged_lsoa_{country}.json", "w") as f:
        json.dump(england_wales_lsoas, f)


def get_lsoas_in_lad(lad):
    url = f"http://data.ons.gov.uk/ons/api/data/dataset/QS201EW.json?pdm/{lad}=LSOA&jsontype=json-stat&totals=false&context=Census&geog=2011STATH"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(data)
        return data
    else:
        print(response.status_code)
