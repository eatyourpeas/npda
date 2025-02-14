from dataclasses import dataclass
from enum import Enum

@dataclass
class PZCode:
    pz_code: str
    name: str

class DummyPZCodes(Enum):
    RCPCH = PZCode(pz_code="PZ999", name="RCPCH")
    NOT_FOUND = PZCode(pz_code="PZ998", name="NOT_FOUND")


pzs = [
    "RM102",
    "RXF05",
    "RNS01",
    "RTGFG",
    "RP5DR",
    "RTH08",
    "RJN71",
    "RC971",
    "RAL26",
    "RALC7",
    "R0A07",
    "RP5BA",
    "RBD01",
    "RYR18",
    "RDDH0",
    "RJL30",
    "RDU50",
    "RNNBX",
    "RJ701",
    "RVV",
    "RWA01",
    "RTR45",
    "RXQ02",
    "RBT20",
    "RYR16",
    "RTD02",
    "RTG02",
    "RN541",
    "RHW01",
    "R1HKH",
    "RXQ50",
    "RRK97",
    "RGT01",
    "RX1RA",
    "RKEQ4",
    "RCF22",
    "RWDDA",
    "RWWWH",
    "RVR",
    "RJL32",
    "RD300",
    "RWEAA",
    "RAX01",
    "R1HNH",
    "R1H12",
    "RH801",
    "RJ611",
    "RFSDA",
    "RJE09",
    "REF12",
    "RD130",
    "RWJ09",
    "RGR50",
    "RWP01",
    "RBS25",
    "R1F01",
    "RDEE4",
    "RJE01",
    "R0B01",
    "RJ122",
    "RWP31",
    "RJZ30",
    "RGN90",
    "RA201",
    "R1K01",
    "RXR20",
    "RXWAT",
    "RK950",
    "RXK02",
    "RWH",
    "RBZ12",
    "RR801",
    "RAS01",
    "RRF02",
    "RAE05",
    "RXL01",
    "RR7EN",
    "RQ301",
    "RHM01",
    "RVY02",
    "RLQ01",
    "RCBCA",
    "RCB55",
    "RJ224",
    "RN707",
    "RTFFS",
    "RLT09",
    "RKB01",
    "RWF03",
    "RPA02",
    "RGP75",
    "RWDLA",
    "RCD01",
    "RQM01",
    "RGN80",
    "RTRAT",
    "RXH06",
    "R0A",
    "RBA11",
    "RJC02",
    "RA723",
    "RMP01",
    "R0B0Q",
    "RRK98",
    "RD816",
    "RAJ01",
    "RFFAA",
    "RNN62",
    "RJ231",
    "RA901",
    "RBN01",
    "RCX70",
    "RAL01",
    "RN506",
    "RXPBA",
    "RXPDA",
    "RXPCP",
    "RVWAE",
    "RFRPA",
    "RTX",
    "RWDLP",
    "RNZ02",
    "RBL14",
    "RQ8L0",
    "RWG02",
    "RA430",
    "RNQ51",
    "RTK01",
    "RMC01",
    "RBK02",
    "RJR",
    "RK5BC",
    "RDE03",
    "RQM91",
    "RXN02",
    "RWY",
    "R1K04",
    "RP401",
    "RAPNM",
    "RQWG0",
    "RYJ01",
    "RRV03",
    "RW6",
    "RTP04",
    "RJZ01",
    "RWFTW",
    "RDU01",
    "RCUEF",
    "RC112",
    "RN325",
    "RL403",
    "RXK01",
    "RWP50",
    "RXF10",
    "RXC",
    "RM301",
    "RF4",
    "RHU03",
    "RNA01",
    "RTE01",
]

NPDA_ORGANISATIONS = [
    {
        "ods_code": "RM102",
        "npda_code": "PZ002",
        "organisation_name": "Norfolk and Norwich University Hospital",
        "trust_name": "NORFOLK AND NORWICH UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXF05",
        "npda_code": "PZ003",
        "organisation_name": "Pinderfields General Hospital and Pontefract General Infirmary",
        "trust_name": "THE MID YORKSHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RNS01",
        "npda_code": "PZ004",
        "organisation_name": "Northampton General Hospital",
        "trust_name": "NORTHAMPTON GENERAL HOSPITAL NHS TRUST",
    },
    {
        "ods_code": "RTGFG",
        "npda_code": "PZ005",
        "organisation_name": "Derbyshire Children's Hospital",
        "trust_name": "UNIVERSITY HOSPITALS OF DERBY AND BURTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RP5DR",
        "npda_code": "PZ006",
        "organisation_name": "Doncaster Royal Infirmary",
        "trust_name": "DONCASTER AND BASSETLAW TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTH08",
        "npda_code": "PZ007",
        "organisation_name": "John Radcliffe Hospital",
        "trust_name": "OXFORD UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJN71",
        "npda_code": "PZ009",
        "organisation_name": "Macclesfield District General Hospital",
        "trust_name": "EAST CHESHIRE NHS TRUST",
    },
    {
        "ods_code": "RC971",
        "npda_code": "PZ010",
        "organisation_name": "Luton and Dunstable Hospital",
        "trust_name": "BEDFORDSHIRE HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RAL26",
        "npda_code": "PZ012",
        "organisation_name": "Barnet General Hospital",
        "trust_name": "ROYAL FREE LONDON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RALC7",
        "npda_code": "PZ014",
        "organisation_name": "Chase Farm Hospital",
        "trust_name": "ROYAL FREE LONDON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R0A07",
        "npda_code": "PZ015",
        "organisation_name": "Wythenshawe Hospital",
        "trust_name": "MANCHESTER UNIVERSITY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RP5BA",
        "npda_code": "PZ016",
        "organisation_name": "Bassetlaw District General Hospital",
        "trust_name": "DONCASTER AND BASSETLAW TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RBD01",
        "npda_code": "PZ017",
        "organisation_name": "Dorset County Hospital",
        "trust_name": "DORSET COUNTY HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RYR18",
        "npda_code": "PZ018",
        "organisation_name": "Worthing Hospital",
        "trust_name": "UNIVERSITY HOSPITALS SUSSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RDDH0",
        "npda_code": "PZ019",
        "organisation_name": "Basildon University Hospital",
        "trust_name": "MID AND SOUTH ESSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJL30",
        "npda_code": "PZ020",
        "organisation_name": "Diana, Princess of Wales Hospital, Grimsby",
        "trust_name": "NORTHERN LINCOLNSHIRE AND GOOLE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RDU50",
        "npda_code": "PZ021",
        "organisation_name": "Wexham Park Hospital",
        "trust_name": "FRIMLEY HEALTH NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RNNBX",
        "npda_code": "PZ022",
        "organisation_name": "West Cumberland Hospital ",
        "trust_name": "NORTH CUMBRIA INTEGRATED CARE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJ701",
        "npda_code": "PZ023",
        "organisation_name": "St George's Hospital, London",
        "trust_name": "ST GEORGE'S UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RVV",
        "npda_code": "PZ024",
        "organisation_name": "East Kent Hospitals University NHS Foundation Trust",
        "trust_name": "EAST KENT HOSPITALS UNIVERSITY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWA01",
        "npda_code": "PZ026",
        "organisation_name": "Hull Royal Infirmary",
        "trust_name": "HULL UNIVERSITY TEACHING HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RTR45",
        "npda_code": "PZ027",
        "organisation_name": "Friarage Hospital ",
        "trust_name": "SOUTH TEES HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXQ02",
        "npda_code": "PZ028",
        "organisation_name": "Stoke Mandeville Hospital ",
        "trust_name": "BUCKINGHAMSHIRE HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RBT20",
        "npda_code": "PZ030",
        "organisation_name": "Leighton Hospital",
        "trust_name": "MID-CHESHIRE HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RYR16",
        "npda_code": "PZ031",
        "organisation_name": "St Richard's Hospital ",
        "trust_name": "UNIVERSITY HOSPITALS SUSSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTD02",
        "npda_code": "PZ032",
        "organisation_name": "Royal Victoria Infirmary, Newcastle Upon Tyne",
        "trust_name": "NEWCASTLE UPON TYNE HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTG02",
        "npda_code": "PZ033",
        "organisation_name": "Queens Hospital, Burton on Trent",
        "trust_name": "UNIVERSITY HOSPITALS OF DERBY AND BURTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RN541",
        "npda_code": "PZ034",
        "organisation_name": "Royal Hampshire County Hospital",
        "trust_name": "HAMPSHIRE HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RHW01",
        "npda_code": "PZ035",
        "organisation_name": "Royal Berkshire Hospital",
        "trust_name": "ROYAL BERKSHIRE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R1HKH",
        "npda_code": "PZ036",
        "organisation_name": "Whipps Cross University Hospital ",
        "trust_name": "BARTS HEALTH NHS TRUST",
    },
    {
        "ods_code": "RXQ50",
        "npda_code": "PZ038",
        "organisation_name": "Wycombe General Hospital ",
        "trust_name": "BUCKINGHAMSHIRE HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RRK97",
        "npda_code": "PZ040",
        "organisation_name": "Birmingham Heartlands Hospital",
        "trust_name": "UNIVERSITY HOSPITALS BIRMINGHAM NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RGT01",
        "npda_code": "PZ041",
        "organisation_name": "Addenbrooke's Hospital",
        "trust_name": "CAMBRIDGE UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RX1RA",
        "npda_code": "PZ042",
        "organisation_name": "Nottingham Children's Hospital ",
        "trust_name": "NOTTINGHAM UNIVERSITY HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RKEQ4",
        "npda_code": "PZ045",
        "organisation_name": "Whittington Hospital, London",
        "trust_name": "WHITTINGTON HEALTH NHS TRUST",
    },
    {
        "ods_code": "RCF22",
        "npda_code": "PZ047",
        "organisation_name": "Airedale General Hospital, Keighley",
        "trust_name": "AIREDALE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWDDA",
        "npda_code": "PZ048",
        "organisation_name": "Lincoln County Hospital ",
        "trust_name": "UNITED LINCOLNSHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RWWWH",
        "npda_code": "PZ049",
        "organisation_name": "Warrington Hospital",
        "trust_name": "WARRINGTON AND HALTON TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RVR",
        "npda_code": "PZ050",
        "organisation_name": "Epsom & St Helier University Hospitals NHS Trust",
        "trust_name": "EPSOM AND ST HELIER UNIVERSITY HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RJL32",
        "npda_code": "PZ053",
        "organisation_name": "Scunthorpe General Hospital",
        "trust_name": "NORTHERN LINCOLNSHIRE AND GOOLE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RD300",
        "npda_code": "PZ054",
        "organisation_name": "Poole General Hospital",
        "trust_name": "UNIVERSITY HOSPITALS DORSET NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWEAA",
        "npda_code": "PZ055",
        "organisation_name": "Leicester Royal Infirmary",
        "trust_name": "UNIVERSITY HOSPITALS OF LEICESTER NHS TRUST",
    },
    {
        "ods_code": "RAX01",
        "npda_code": "PZ057",
        "organisation_name": "Kingston Hospital",
        "trust_name": "KINGSTON HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R1HNH",
        "npda_code": "PZ058",
        "organisation_name": "Newham University Hospital",
        "trust_name": "BARTS HEALTH NHS TRUST",
    },
    {
        "ods_code": "R1H12",
        "npda_code": "PZ059",
        "organisation_name": "The Royal London Hospital ",
        "trust_name": "BARTS HEALTH NHS TRUST",
    },
    {
        "ods_code": "RH801",
        "npda_code": "PZ060",
        "organisation_name": "Royal Devon and Exeter Hospital",
        "trust_name": "ROYAL DEVON UNIVERSITY HEALTHCARE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJ611",
        "npda_code": "PZ062",
        "organisation_name": "Croydon University Hospital",
        "trust_name": "CROYDON HEALTH SERVICES NHS TRUST",
    },
    {
        "ods_code": "RFSDA",
        "npda_code": "PZ064",
        "organisation_name": "Chesterfield Royal Hospital",
        "trust_name": "CHESTERFIELD ROYAL HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJE09",
        "npda_code": "PZ065",
        "organisation_name": "County Hospital Stafford",
        "trust_name": "UNIVERSITY HOSPITALS OF NORTH MIDLANDS NHS TRUST",
    },
    {
        "ods_code": "REF12",
        "npda_code": "PZ067",
        "organisation_name": "Royal Cornwall Hospital",
        "trust_name": "ROYAL CORNWALL HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RD130",
        "npda_code": "PZ068",
        "organisation_name": "Royal United Hospital",
        "trust_name": "ROYAL UNITED HOSPITALS BATH NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWJ09",
        "npda_code": "PZ069",
        "organisation_name": "Stepping Hill Hospital",
        "trust_name": "STOCKPORT NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RGR50",
        "npda_code": "PZ072",
        "organisation_name": "West Suffolk Hospital, Bury St Edmunds",
        "trust_name": "WEST SUFFOLK NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWP01",
        "npda_code": "PZ073",
        "organisation_name": "Alexandra Hospital ",
        "trust_name": "WORCESTERSHIRE ACUTE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RBS25",
        "npda_code": "PZ074",
        "organisation_name": "Alder Hey Children's Hospital",
        "trust_name": "ALDER HEY CHILDREN'S NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R1F01",
        "npda_code": "PZ075",
        "organisation_name": "St Mary's Hospital, Isle of Wight",
        "trust_name": "ISLE OF WIGHT NHS TRUST",
    },
    {
        "ods_code": "RDEE4",
        "npda_code": "PZ076",
        "organisation_name": "Colchester General Hospital",
        "trust_name": "EAST SUFFOLK AND NORTH ESSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJE01",
        "npda_code": "PZ078",
        "organisation_name": "Royal Stoke University Hospital",
        "trust_name": "UNIVERSITY HOSPITALS OF NORTH MIDLANDS NHS TRUST",
    },
    {
        "ods_code": "R0B01",
        "npda_code": "PZ080",
        "organisation_name": "Sunderland Royal Hospital",
        "trust_name": "SOUTH TYNESIDE AND SUNDERLAND NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJ122",
        "npda_code": "PZ082",
        "organisation_name": "Evelina Childrens Hospital",
        "trust_name": "GUY'S AND ST THOMAS' NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWP31",
        "npda_code": "PZ084",
        "organisation_name": "Kidderminster Hospital",
        "trust_name": "WORCESTERSHIRE ACUTE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RJZ30",
        "npda_code": "PZ085",
        "organisation_name": "Princess Royal University Hospital",
        "trust_name": "KING'S COLLEGE HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RGN90",
        "npda_code": "PZ086",
        "organisation_name": "Hinchingbrooke Hospital",
        "trust_name": "NORTH WEST ANGLIA NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RA201",
        "npda_code": "PZ088",
        "organisation_name": "Royal Surrey County Hospital",
        "trust_name": "ROYAL SURREY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R1K01",
        "npda_code": "PZ089",
        "organisation_name": "Northwick Park Hospital",
        "trust_name": "LONDON NORTH WEST UNIVERSITY HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RXR20",
        "npda_code": "PZ091",
        "organisation_name": "Royal Blackburn Hospital",
        "trust_name": "EAST LANCASHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RXWAT",
        "npda_code": "PZ094",
        "organisation_name": "Princess Royal Hospital",
        "trust_name": "SHREWSBURY AND TELFORD HOSPITAL NHS TRUST",
    },
    {
        "ods_code": "RK950",
        "npda_code": "PZ096",
        "organisation_name": "Derriford Hospital",
        "trust_name": "UNIVERSITY HOSPITALS PLYMOUTH NHS TRUST",
    },
    {
        "ods_code": "RXK02",
        "npda_code": "PZ097",
        "organisation_name": "City Hospital, Birmingham",
        "trust_name": "SANDWELL AND WEST BIRMINGHAM HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RWH",
        "npda_code": "PZ099",
        "organisation_name": "East and North Hertfordshire NHS Trust",
        "trust_name": "EAST AND NORTH HERTFORDSHIRE NHS TRUST",
    },
    {
        "ods_code": "RBZ12",
        "npda_code": "PZ100",
        "organisation_name": "North Devon District Hospital",
        "trust_name": "ROYAL DEVON UNIVERSITY HEALTHCARE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RR801",
        "npda_code": "PZ101",
        "organisation_name": "Leeds Childrens' Hospital",
        "trust_name": "LEEDS TEACHING HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RAS01",
        "npda_code": "PZ102",
        "organisation_name": "The Hillingdon Hospital",
        "trust_name": "THE HILLINGDON HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RRF02",
        "npda_code": "PZ104",
        "organisation_name": "Royal Albert Edward Infirmary",
        "trust_name": "WRIGHTINGTON, WIGAN AND LEIGH NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RAE05",
        "npda_code": "PZ105",
        "organisation_name": "St Luke's Hospital",
        "trust_name": "BRADFORD TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXL01",
        "npda_code": "PZ106",
        "organisation_name": "Victoria Hospital, Blackpool",
        "trust_name": "BLACKPOOL TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RR7EN",
        "npda_code": "PZ107",
        "organisation_name": "Queen Elizabeth Hospital, Gateshead",
        "trust_name": "GATESHEAD HEALTH NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RQ301",
        "npda_code": "PZ108",
        "organisation_name": "Birmingham Children's Hospital",
        "trust_name": "BIRMINGHAM WOMEN'S AND CHILDREN'S NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RHM01",
        "npda_code": "PZ109",
        "organisation_name": "Southampton Children’s Hospital",
        "trust_name": "UNIVERSITY HOSPITAL SOUTHAMPTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RVY02",
        "npda_code": "PZ110",
        "organisation_name": "Ormskirk & District General Hospital",
        "trust_name": "SOUTHPORT AND ORMSKIRK HOSPITAL NHS TRUST",
    },
    {
        "ods_code": "RLQ01",
        "npda_code": "PZ111",
        "organisation_name": "Hereford County Hospital",
        "trust_name": "WYE VALLEY NHS TRUST",
    },
    {
        "ods_code": "RCBCA",
        "npda_code": "PZ112",
        "organisation_name": "Scarborough General Hospital",
        "trust_name": "YORK AND SCARBOROUGH TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RCB55",
        "npda_code": "PZ114",
        "organisation_name": "The York Hospital",
        "trust_name": "YORK AND SCARBOROUGH TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJ224",
        "npda_code": "PZ118",
        "organisation_name": "University Hospital Lewisham",
        "trust_name": "LEWISHAM AND GREENWICH NHS TRUST",
    },
    {
        "ods_code": "RN707",
        "npda_code": "PZ119",
        "organisation_name": "Darent Valley Hospital, Dartford",
        "trust_name": "DARTFORD AND GRAVESHAM NHS TRUST",
    },
    {
        "ods_code": "RTFFS",
        "npda_code": "PZ120",
        "organisation_name": "North Tyneside General Hospital",
        "trust_name": "NORTHUMBRIA HEALTHCARE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RLT09",
        "npda_code": "PZ121",
        "organisation_name": "George Eliot Hospital",
        "trust_name": "GEORGE ELIOT HOSPITAL NHS TRUST",
    },
    {
        "ods_code": "RKB01",
        "npda_code": "PZ122",
        "organisation_name": "University Hospital, Coventry ",
        "trust_name": "UNIVERSITY HOSPITALS COVENTRY AND WARWICKSHIRE NHS TRUST",
    },
    {
        "ods_code": "RWF03",
        "npda_code": "PZ125",
        "organisation_name": "Maidstone Hospital",
        "trust_name": "MAIDSTONE AND TUNBRIDGE WELLS NHS TRUST",
    },
    {
        "ods_code": "RPA02",
        "npda_code": "PZ126",
        "organisation_name": "Medway Maritime Hospital",
        "trust_name": "MEDWAY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RGP75",
        "npda_code": "PZ127",
        "organisation_name": "James Paget Hospital",
        "trust_name": "JAMES PAGET UNIVERSITY HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWDLA",
        "npda_code": "PZ128",
        "organisation_name": "Pilgrim Hospital ",
        "trust_name": "UNITED LINCOLNSHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RCD01",
        "npda_code": "PZ129",
        "organisation_name": "Harrogate District Hospital",
        "trust_name": "HARROGATE AND DISTRICT NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RQM01",
        "npda_code": "PZ130",
        "organisation_name": "Chelsea and Westminster Hospital",
        "trust_name": "CHELSEA AND WESTMINSTER HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RGN80",
        "npda_code": "PZ131",
        "organisation_name": "Peterborough City Hospital",
        "trust_name": "NORTH WEST ANGLIA NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTRAT",
        "npda_code": "PZ133",
        "organisation_name": "James Cook University Hospital ",
        "trust_name": "SOUTH TEES HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXH06",
        "npda_code": "PZ135",
        "organisation_name": "Royal Alexandra Hospital, Brighton",
        "trust_name": "UNIVERSITY HOSPITALS SUSSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R0A",
        "npda_code": "PZ136",
        "organisation_name": "Central Manchester University Hospitals NHS Foundation Trust",
        "trust_name": "MANCHESTER UNIVERSITY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RBA11",
        "npda_code": "PZ137",
        "organisation_name": "Musgrove Park Hospital",
        "trust_name": "SOMERSET NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJC02",
        "npda_code": "PZ138",
        "organisation_name": "Warwick Hospital",
        "trust_name": "SOUTH WARWICKSHIRE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RA723",
        "npda_code": "PZ139",
        "organisation_name": "Bristol Royal Hospital for Children",
        "trust_name": "UNIVERSITY HOSPITALS BRISTOL AND WESTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RMP01",
        "npda_code": "PZ140",
        "organisation_name": "Tameside General Hospital",
        "trust_name": "TAMESIDE AND GLOSSOP INTEGRATED CARE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R0B0Q",
        "npda_code": "PZ141",
        "organisation_name": "South Tyneside District Hospital",
        "trust_name": "SOUTH TYNESIDE AND SUNDERLAND NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RRK98",
        "npda_code": "PZ144",
        "organisation_name": "Good Hope Hospital, Sutton Coldfield",
        "trust_name": "UNIVERSITY HOSPITALS BIRMINGHAM NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RD816",
        "npda_code": "PZ145",
        "organisation_name": "Milton Keynes Hospital",
        "trust_name": "MILTON KEYNES UNIVERSITY HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RAJ01",
        "npda_code": "PZ146",
        "organisation_name": "Southend University Hospital",
        "trust_name": "MID AND SOUTH ESSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RFFAA",
        "npda_code": "PZ149",
        "organisation_name": "Barnsley Hospital",
        "trust_name": "BARNSLEY HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RNN62",
        "npda_code": "PZ150",
        "organisation_name": "Cumberland Infirmary",
        "trust_name": "NORTH CUMBRIA INTEGRATED CARE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RJ231",
        "npda_code": "PZ151",
        "organisation_name": "Queen Elizabeth Hospital, Woolwich",
        "trust_name": "LEWISHAM AND GREENWICH NHS TRUST",
    },
    {
        "ods_code": "RA901",
        "npda_code": "PZ152",
        "organisation_name": "Torbay Hospital",
        "trust_name": "TORBAY AND SOUTH DEVON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RBN01",
        "npda_code": "PZ153",
        "organisation_name": "Whiston Hospital",
        "trust_name": "ST HELENS AND KNOWSLEY TEACHING HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RCX70",
        "npda_code": "PZ156",
        "organisation_name": "Queen Elizabeth Hospital, Kings Lynn",
        "trust_name": "QUEEN ELIZABETH HOSPITAL KINGS LYNN NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RAL01",
        "npda_code": "PZ157",
        "organisation_name": "Royal Free Hospital",
        "trust_name": "ROYAL FREE LONDON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RN506",
        "npda_code": "PZ159",
        "organisation_name": "Basingstoke and North Hampshire Hospital",
        "trust_name": "HAMPSHIRE HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXPBA",
        "npda_code": "PZ160",
        "organisation_name": "Bishop Auckland Hospital",
        "trust_name": "COUNTY DURHAM AND DARLINGTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXPDA",
        "npda_code": "PZ161",
        "organisation_name": "Darlington Memorial Hospital",
        "trust_name": "COUNTY DURHAM AND DARLINGTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXPCP",
        "npda_code": "PZ162",
        "organisation_name": "University Hospital of North Durham",
        "trust_name": "COUNTY DURHAM AND DARLINGTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RVWAE",
        "npda_code": "PZ163",
        "organisation_name": "University Hospital of North Tees and University Hospital of Hartlepool",
        "trust_name": "NORTH TEES AND HARTLEPOOL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RFRPA",
        "npda_code": "PZ164",
        "organisation_name": "Rotherham Hospital",
        "trust_name": "THE ROTHERHAM NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTX",
        "npda_code": "PZ167",
        "organisation_name": "University Hospitals of Morecambe Bay NHS Foundation Trust ",
        "trust_name": "UNIVERSITY HOSPITALS OF MORECAMBE BAY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWDLP",
        "npda_code": "PZ168",
        "organisation_name": "Grantham and District Hospital",
        "trust_name": "UNITED LINCOLNSHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RNZ02",
        "npda_code": "PZ169",
        "organisation_name": "Salisbury District Hospital",
        "trust_name": "SALISBURY NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RBL14",
        "npda_code": "PZ170",
        "organisation_name": "Arrowe Park Hospital",
        "trust_name": "WIRRAL UNIVERSITY TEACHING HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RQ8L0",
        "npda_code": "PZ171",
        "organisation_name": "Broomfield Hospital",
        "trust_name": "MID AND SOUTH ESSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWG02",
        "npda_code": "PZ172",
        "organisation_name": "West Hertfordshire Hospitals NHS Trust ",
        "trust_name": "WEST HERTFORDSHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RA430",
        "npda_code": "PZ173",
        "organisation_name": "Yeovil District Hospital",
        "trust_name": "YEOVIL DISTRICT HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RNQ51",
        "npda_code": "PZ174",
        "organisation_name": "Kettering General Hospital",
        "trust_name": "KETTERING GENERAL HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTK01",
        "npda_code": "PZ176",
        "organisation_name": "St Peter's Hospital",
        "trust_name": "ASHFORD AND ST PETER'S HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RMC01",
        "npda_code": "PZ177",
        "organisation_name": "Royal Bolton Hospital",
        "trust_name": "BOLTON NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RBK02",
        "npda_code": "PZ178",
        "organisation_name": "Manor Hospital, Walsall",
        "trust_name": "WALSALL HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RJR",
        "npda_code": "PZ179",
        "organisation_name": "Countess of Chester Hospital NHS Trust",
        "trust_name": "COUNTESS OF CHESTER HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RK5BC",
        "npda_code": "PZ180",
        "organisation_name": "Kings Mill Hospital",
        "trust_name": "SHERWOOD FOREST HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RDE03",
        "npda_code": "PZ181",
        "organisation_name": "Ipswich Hospital",
        "trust_name": "EAST SUFFOLK AND NORTH ESSEX NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RQM91",
        "npda_code": "PZ182",
        "organisation_name": "West Middlesex University Hospital",
        "trust_name": "CHELSEA AND WESTMINSTER HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RXN02",
        "npda_code": "PZ183",
        "organisation_name": "Royal Preston Hospital",
        "trust_name": "LANCASHIRE TEACHING HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWY",
        "npda_code": "PZ186",
        "organisation_name": "Calderdale & Huddersfield NHS Foundation Trust",
        "trust_name": "CALDERDALE AND HUDDERSFIELD NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "R1K04",
        "npda_code": "PZ191",
        "organisation_name": "Ealing Hospital",
        "trust_name": "LONDON NORTH WEST UNIVERSITY HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RP401",
        "npda_code": "PZ196",
        "organisation_name": "Great Ormond Street Hospital",
        "trust_name": "GREAT ORMOND STREET HOSPITAL FOR CHILDREN NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RAPNM",
        "npda_code": "PZ199",
        "organisation_name": "North Middlesex University Hospital",
        "trust_name": "NORTH MIDDLESEX UNIVERSITY HOSPITAL NHS TRUST",
    },
    {
        "ods_code": "RQWG0",
        "npda_code": "PZ200",
        "organisation_name": "Princess Alexandra Hospital, Harlow (inc Rectory Lane Health Center, Essex) ",
        "trust_name": "PRINCESS ALEXANDRA HOSPITAL NHS TRUST",
    },
    {
        "ods_code": "RYJ01",
        "npda_code": "PZ202",
        "organisation_name": "St Marys Hospital, Imperial College, London",
        "trust_name": "IMPERIAL COLLEGE HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RRV03",
        "npda_code": "PZ203",
        "organisation_name": "University College London Hospital",
        "trust_name": "UNIVERSITY COLLEGE LONDON HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RW6",
        "npda_code": "PZ206",
        "organisation_name": "The Pennine Acute Hospitals NHS Trust",
        "trust_name": "NORTHERN CARE ALLIANCE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTP04",
        "npda_code": "PZ213",
        "organisation_name": "East Surrey Hospital",
        "trust_name": "SURREY AND SUSSEX HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RJZ01",
        "npda_code": "PZ215",
        "organisation_name": "Kings College Hospital, London",
        "trust_name": "KING'S COLLEGE HOSPITAL NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RWFTW",
        "npda_code": "PZ216",
        "organisation_name": "Tunbridge Wells Hospital",
        "trust_name": "MAIDSTONE AND TUNBRIDGE WELLS NHS TRUST",
    },
    {
        "ods_code": "RDU01",
        "npda_code": "PZ218",
        "organisation_name": "Frimley Park Hospital ",
        "trust_name": "FRIMLEY HEALTH NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RCUEF",
        "npda_code": "PZ219",
        "organisation_name": "Sheffield Childrens Hospital",
        "trust_name": "SHEFFIELD CHILDREN'S NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RC112",
        "npda_code": "PZ220",
        "organisation_name": "Bedford Hospital",
        "trust_name": "BEDFORDSHIRE HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RN325",
        "npda_code": "PZ221",
        "organisation_name": "Great Western Hospital",
        "trust_name": "GREAT WESTERN HOSPITALS NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RL403",
        "npda_code": "PZ222",
        "organisation_name": "New Cross Hospital, Wolverhampton",
        "trust_name": "THE ROYAL WOLVERHAMPTON NHS TRUST",
    },
    {
        "ods_code": "RXK01",
        "npda_code": "PZ223",
        "organisation_name": "Sandwell General Hospital",
        "trust_name": "SANDWELL AND WEST BIRMINGHAM HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RWP50",
        "npda_code": "PZ225",
        "organisation_name": "Worcestershire Royal Hospital",
        "trust_name": "WORCESTERSHIRE ACUTE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RXF10",
        "npda_code": "PZ226",
        "organisation_name": "Dewsbury & District Hospital",
        "trust_name": "THE MID YORKSHIRE HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RXC",
        "npda_code": "PZ230",
        "organisation_name": "East Sussex Healthcare NHS Trust/Conquest Hospital ",
        "trust_name": "EAST SUSSEX HEALTHCARE NHS TRUST",
    },
    {
        "ods_code": "RM301",
        "npda_code": "PZ231",
        "organisation_name": "Salford Royal Foundation Trust",
        "trust_name": "NORTHERN CARE ALLIANCE NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RF4",
        "npda_code": "PZ232",
        "organisation_name": "BHR University Hospitals NHS Trust ",
        "trust_name": "BARKING, HAVERING AND REDBRIDGE UNIVERSITY HOSPITALS NHS TRUST",
    },
    {
        "ods_code": "RHU03",
        "npda_code": "PZ238",
        "organisation_name": "Queen Alexandra Hospital, Portsmouth",
        "trust_name": "PORTSMOUTH HOSPITALS UNIVERSITY NATIONAL HEALTH SERVICE TRUST",
    },
    {
        "ods_code": "RNA01",
        "npda_code": "PZ240",
        "organisation_name": "Russells Hall Hospital",
        "trust_name": "THE DUDLEY GROUP NHS FOUNDATION TRUST",
    },
    {
        "ods_code": "RTE01",
        "npda_code": "PZ242",
        "organisation_name": "Gloucestershire Royal Hospital",
        "trust_name": "GLOUCESTERSHIRE HOSPITALS NHS FOUNDATION TRUST",
    },
]
