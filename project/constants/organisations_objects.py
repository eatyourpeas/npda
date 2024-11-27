from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class PaediatricDiabetesUnit:
    pz_code: str


@dataclass
class Trust:
    ods_code: str
    name: str
    address_line_1: str
    address_line_2: str
    town: str
    postcode: str
    country: str
    telephone: Optional[str]
    website: Optional[str]
    active: bool
    published_at: Optional[str]


@dataclass
class IntegratedCareBoard:
    boundary_identifier: str
    name: str
    ods_code: str


@dataclass
class NHSEnglandRegion:
    region_code: str
    publication_date: str
    boundary_identifier: str
    name: str


@dataclass
class OpenUKNetwork:
    name: str
    boundary_identifier: str
    country: str
    publication_date: str


@dataclass
class Country:
    boundary_identifier: str
    name: str
